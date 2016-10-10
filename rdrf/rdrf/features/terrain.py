import os
import logging
from contextlib import contextmanager
from aloe import before, after, around, world
from selenium import webdriver
from . import steps
from selenium.common.exceptions import NoAlertPresentException

logger = logging.getLogger(__name__)

def get_desired_capabilities(browser):
    return {
        'firefox': webdriver.DesiredCapabilities.FIREFOX,
        'chrome': webdriver.DesiredCapabilities.CHROME,
    }.get(browser, webdriver.DesiredCapabilities.FIREFOX)


@around.all
@contextmanager
def with_browser():
    desired_capabilities = get_desired_capabilities(os.environ.get('TEST_BROWSER'))

    world.browser = webdriver.Remote(
        desired_capabilities=desired_capabilities,
        command_executor="http://hub:4444/wd/hub"
    )
    world.browser.implicitly_wait(int(os.environ['TEST_WAIT']))

    yield

    if do_teardown():
        world.browser.quit()

    delattr(world, "browser")

def reset_snapshot_dict():
    world.snapshot_dict = {}
    logger.info("set snapshot_dict to %s" % world.snapshot_dict)


def set_site_url():
    world.site_url = steps.get_site_url(default_url="http://web:8000")
    logger.info("world.site_url = %s" % world.site_url)


def do_teardown():
    return ('LETTUCE_DISABLE_TEARDOWN' not in os.environ or
            os.environ['LETTUCE_DISABLE_TEARDOWN'] == '0')


@before.all
def before_all():
    logger.info('')
    reset_snapshot_dict()
    set_site_url()
    steps.save_minimal_snapshot()


# @after.all
# def after_all(total):
#    logger.info('Scenarios: {0} Passed: {1}'.format(total.scenarios_ran, total.scenarios_passed))


def delete_cookies():
    # delete all cookies so when we browse to a url at the start we have to log in
    world.browser.delete_all_cookies()


@before.each_example
def before_scenario(scenario, outline, steps):
    logger.info('Scenario: ' + scenario.name)
    delete_cookies()


@after.each_example
def after_scenario(scenario, outline, test_steps):
    passfail = "PASS" if test_steps and all(step.passed for step in test_steps) else "FAIL"
    world.browser.get_screenshot_as_file(
        "/data/{0}-{1}.png".format(passfail, scenario.name))
    if do_teardown():
        steps.restore_minimal_snapshot()


@after.each_step
def screenshot_step(step):
    if not step.passed and step.scenario is not None:
        step_name = "%s_%s" % (step.scenario.name, step)
        step_name = step_name.replace(" ", "")
        file_name = "/data/False-step-{0}.png".format(step_name)
        world.browser.get_screenshot_as_file(file_name)

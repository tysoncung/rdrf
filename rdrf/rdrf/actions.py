import logging
logger = logging.getLogger("registry_log")


class ActionExecutor(object):
    def __init__(self, action_dict):
        self.action_dict = action_dict

    def run(self):
        rpc_command = self.action_dict['rpc_command']
        rpc_args = self.action_dict['args']
        rpc_function = self._locate_command_function(rpc_command)
        client_response = {}

        if rpc_function:
            try:
                result = rpc_function(*rpc_args)
                client_response['result'] = result
                client_response['status'] = 'success'
            except Exception, ex:
                client_response['status'] = 'fail'
                client_response['error'] = ex.message
        else:
            client_response['status'] = 'fail'
            client_response['error'] = 'could not locate command: %s' % rpc_command

        logger.info("rpm command: %s args: %s result: %s" % (rpc_command, rpc_args, client_response))
        return client_response

    def _locate_command_function(self, rpc_command):
        rpc_module = __import__('rpc_command')
        if hasattr(rpc_command, rpc_command):
            rpc_function = getattr(rpc_module, rpc_command)
            if callable(rpc_function):
                return rpc_function

(function ($) {

        let required_cde_inputs = {};
        let calculated_cde_inputs = {}
        let patient_date_of_birth = '';
        let patient_sex = '';

        const update_function = function (calculated_cdes) {
            // console.log(`UPDATE FUNCTION: ${calculated_cdes}`);

            calculated_cdes.forEach(cde_code => {
                // console.log(`UPDATE FUNCTION CDE: ${calculated_cdes} : ${cde_code}`);
                // Retrieve all values of input
                calculated_cde_inputs_json_values = {};
                calculated_cde_inputs[cde_code].forEach((required_input_cde) => {

                    let cde_value = $(`[id$=__${required_input_cde}]`).val();
                    // console.log(`${required_input_cde}: ${cde_value}`);

                    // check if it is a date like dd-mm-yyyy and convert it in yyyy-mm-dd
                    if (moment(cde_value, "D-M-YYYY",true).isValid()) {
                        // console.log(`Detecting wrong date: ${required_input_cde}: ${cde_value}`)
                        // console.log(moment(cde_value))
                        cde_value = moment(cde_value, "D-M-YYYY",true).format('YYYY-MM-DD');
                        // console.log(`New date: ${cde_value}`);
                    }

                    // check if it is a number and convert it in a number
                    if ($(`[id$=__${required_input_cde}]`).attr('type') === 'number') {
                        cde_value = parseFloat(cde_value);
                        // console.log(`convert type in number ${required_input_cde}: ${cde_value}`)
                    }


                    calculated_cde_inputs_json_values[required_input_cde] = cde_value;
                });

                const body = {
                    'cde_code': cde_code,
                    'patient_date_of_birth': patient_date_of_birth,
                    'patient_sex': patient_sex,
                    'form_values': calculated_cde_inputs_json_values
                };
                // console.log("BODY json");
                // console.log(body);
                fetch(`/api/v1/calculatedcdes/`, {
                    method: 'post',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': $("[name=csrfmiddlewaretoken]").val()
                    },
                    body: JSON.stringify(body)
                })
                    .then(function (response) {
                        return response.json();
                    })
                    .then(function (myJson) {
                        // console.log(`New value: ${cde_code} ${myJson}`);
                        // if new value change it and display an notification
                        $(`[id$=__${cde_code}]`).val(myJson)
                        $(`[id$=__${cde_code}]`).trigger("change");
                    });
            });
        }

        $.fn.add_calculation = function (options) {

            patient_date_of_birth = options.patient_date_of_birth;
            patient_sex = options.patient_sex;

            calculated_cde_inputs[options.observer] = options.cde_inputs;

            options.cde_inputs.forEach((input_cde_code) => {
                // find the DOM id of the matching input

                // record the input in an array so we can assign the
                required_cde_inputs[input_cde_code] = required_cde_inputs[input_cde_code] != undefined ?
                    [...required_cde_inputs[input_cde_code], options.observer] : [options.observer];
            });

            // console.log(`ADD CALCULTATION ${options.observer}`);
            // console.log(required_cde_inputs);

            try {
                // call on initial page load
                // console.log([options.observer]);
                update_function([options.observer]); //call it to ensure if calculation changes on server
                // we are always in sync(RDR-426 )

                //update the onchange
                Object.keys(required_cde_inputs).forEach(function (cde_input) {
                    $(`[id$=__${cde_input}]`).off("change");
                    $(`[id$=__${cde_input}]`).on('change keyup', _.debounce((e) => {update_function(required_cde_inputs[cde_input])}, 250))
                });

            } catch (err) {
                alert(err);
            }
        };

    }
    (jQuery)
)
;

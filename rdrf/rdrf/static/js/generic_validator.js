// Plumbing code tp launch a constructor form for a DE value and return it back to the main form



function goodValue(element) {
    var indicator = $(element).next(".validationindicator");
    if (indicator.hasClass("validity invalid")) {
        indicator.removeClass('validity invalid');
    }
    indicator.addClass("validity valid");
}

function badValue(element) {
    var indicator = $(element).next(".validationindicator");
    if (indicator.hasClass("validity valid")) {
        indicator.removeClass('validity valid');
    }
    indicator.addClass("validity invalid");
}

function generic_constructor(element, constructorName, constructorFormUrl) {
   // element here is the constructor button next to the input field - we have
   // to use navigate via jquery traversal as the field may be in a multisection and have been cloned
   function updateValue(value) {
       var textField = $(element).closest("td").find("input[type='text']");
       textField.val(value);  // we assume that the DE is text input field
       textField.trigger("keyup");
   }
   var w = window.open(constructorFormUrl, "Construct " + constructorName, "location=no,width=800,height=600,scrollbars=yes,top=100,left=100,resizable = no");
   // NB this function is/must be called on the child form to allow the constructed data value to be passed back to the form
   w.updateParentForm = updateValue;

}

function generic_validate(element, rpcEndPoint, rpcCommand) {
    // element is the text box
    var value = $(element).val();
    var csrfToken = $("input[name='csrfmiddlewaretoken']").val(); // this will/must appear on our django form

    var rpc = new RPC.RPC(rpcEndPoint, csrfToken);
    rpc.send(rpcCommand, [value], function (response) {
        var isValid = response.result;
        if (isValid) {
            goodValue(element);
        }
        else {
            badValue(element);
        }
    });
}
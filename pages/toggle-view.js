
function setVisible(element,visible) {
    // Set the visibility of this toggle-view element
    // element: the html element corresponding to the toggle button
    // visible: true = show, false = hide, any other value = toggle

    console.log("Toggled.");
    let body = document.getElementById(element.id + ".b");
    if (body.style.display == "none") {
        body.style.display = "block";
        element.className = "fa fa-minus-square toggle-view";
    } else {
        body.style.display = "none";
        element.className = "fa fa-plus-square toggle-view";
    }
}

export function loadToggleView() {
    let togglers = document.getElementsByClassName("toggle-view");

    for (let t of togglers) {
        t.addEventListener("click", function() {
            setVisible(this);
        });
    }
}
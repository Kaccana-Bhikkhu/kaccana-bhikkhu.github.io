
function setVisible(element,newVisible) {
    // Set the visibility of this toggle-view element
    // element: the html element corresponding to the toggle button
    // newVisible: true = show, false = hide, null = no change, any other value = toggle

    if (newVisible == null)
        return;

    let body = document.getElementById(element.id + ".b");
    let isVisible = body.style.display != "none";

    if (newVisible == isVisible)
        return;

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

    let params = new URLSearchParams(location.search.slice(1));
    let initView = params.has("showAll") ? true : (params.has("hideAll") ? false : null)

    for (let t of togglers) {
        setVisible(t,initView)
        t.addEventListener("click", function() {
            setVisible(this,"toggle");
        });
    }
}
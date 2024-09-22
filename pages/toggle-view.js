import {frameSearch, setFrameSearch} from './frame.js';

function setVisible(element,newVisible,changeURL) {
    // Set the visibility of this toggle-view element
    // element: the html element corresponding to the toggle button
    // newVisible: true = show, false = hide, null = no change, any other value = toggle
    // if changeURL, then update the URL hash query component

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

    if (changeURL) {
        let params = frameSearch();
        let toggled = (params.get("toggle") || "").split(".");
        if (toggled[0] == "")
            toggled.splice(0,1);
        let index = toggled.indexOf(element.id);
        if (index == -1) {
            toggled.push(element.id);
        } else {
            toggled.splice(index,1);
        }
        params.set("toggle",toggled.join("."));
        setFrameSearch(params);
    }
}

export function loadToggleView() {
    let params = frameSearch()
    let initView = params.has("showAll") ? true : (params.has("hideAll") ? false : null)
    let toggled = (params.get("toggle") || "").split(".");
    if (toggled[0] == "")
        toggled.splice(0,1);

    let togglers = document.getElementsByClassName("toggle-view");
    for (let t of togglers) {
        if ((initView == null) || (toggled.indexOf(t.id) == -1))
            setVisible(t,initView);
        else
            setVisible(t,!initView);
        t.addEventListener("click", function() {
            setVisible(this,"toggle",true);
        });
    }
}
import "./test-dijit.css";
import * as Dialog from "dijit/Dialog";

export function test() {
    const dlg = new Dialog.default({
        content: 'Hello from dijit/Dialog test!<br/>CSS colored <span class="test-red">red text</span>!'
    });
    dlg.show();
}

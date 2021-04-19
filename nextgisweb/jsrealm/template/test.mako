<%inherit file='nextgisweb:templates/base.mako' />

<button id="testDijit">Dijit</button>
<button id="testLodash">Lodash</button>
<button id="testMixed">Mixed</button>
<button id="testPolyfill">Polyfill</button>
<button id="testTypescript">Typescript</button>
<button id="testTranslation">Translation</button>

<script>
    require(["dojo/domReady!"], function () {
        document.getElementById("testDijit").onclick = function () {
            require(['@nextgisweb/jsrealm/test/dijit'], function (module) {
                module.test();
            })
        };
        document.getElementById("testLodash").onclick = function () {
            require(['@nextgisweb/jsrealm/test/lodash'], function (module) {
                module.test();
            })
        };
        document.getElementById("testMixed").onclick = function () {
            require(['@nextgisweb/jsrealm/test/mixed'], function (module) {
                module.test();
            })
        };
        document.getElementById("testPolyfill").onclick = function () {
            require(['@nextgisweb/jsrealm/test/polyfill'], function (module) {
                module.test();
            })
        };
        document.getElementById("testTypescript").onclick = function () {
            require(['@nextgisweb/jsrealm/test/typescript'], function (module) {
                module.test();
            })
        };
        document.getElementById("testTranslation").onclick = function () {
            require(['@nextgisweb/jsrealm/test/translation'], function (module) {
                module.test();
            })
        };
    })
</script>
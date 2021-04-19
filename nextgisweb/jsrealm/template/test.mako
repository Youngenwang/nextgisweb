<%inherit file='nextgisweb:templates/base.mako' />

<button id="testDijit">Test dijit</button>
<button id="testLodash">Test lodash</button>
<button id="testMixed">Test mixed</button>
<button id="testPolyfill">Test polyfill</button>
<button id="testTypescript">Test typescript</button>

<script>
    require(["dojo/domReady!"], function () {
        document.getElementById("testDijit").onclick = function () {
            require(['@nextgisweb/jsrealm/test-dijit'], function (module) {
                module.test();
            })
        };
        document.getElementById("testLodash").onclick = function () {
            require(['@nextgisweb/jsrealm/test-lodash'], function (module) {
                module.test();
            })
        };
        document.getElementById("testMixed").onclick = function () {
            require(['@nextgisweb/jsrealm/test-mixed'], function (module) {
                module.test();
            })
        };
        document.getElementById("testPolyfill").onclick = function () {
            require(['@nextgisweb/jsrealm/test-polyfill'], function (module) {
                module.test();
            })
        };
        document.getElementById("testTypescript").onclick = function () {
            require(['@nextgisweb/jsrealm/test-typescript'], function (module) {
                module.test();
            })
        };
    })
</script>
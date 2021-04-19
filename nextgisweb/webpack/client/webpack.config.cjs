const path = require('path');
const fs = require('fs');

const WebpackAssetsManifest = require('webpack-assets-manifest');

const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const { VueLoaderPlugin } = require('vue-loader');

const entryList = {};

const configRoot = process.env.npm_package_config_nextgisweb_webpack_root;
const configExternals = process.env.npm_package_config_nextgisweb_webpack_external.split(',');
const packageJson = JSON.parse(fs.readFileSync(`${configRoot}/package.json`));

for (const ws of packageJson.workspaces) {
    const subPackageJSON = JSON.parse(fs.readFileSync(`${configRoot}/${ws}/package.json`));
    if ('entry' in subPackageJSON) {
        for (const entryFileName of subPackageJSON.entry) {
            let entryName = entryFileName;
            if (entryFileName.endsWith('.js')) {
                entryName = entryFileName.slice(0, -3);
            }
            if (entryFileName.endsWith('.ts')) {
                entryName = entryFileName.slice(0, -3);
            }
            const entryFullPath = `${configRoot}/${ws}/${entryFileName}`;
            entryList[`${subPackageJSON.name}/${entryName}`] = entryFullPath;
        }
    }
}

module.exports = {
    mode: 'development',
    devtool: 'source-map',
    entry: entryList,
    resolve: {
        alias: {
            "vue$": "vue/dist/vue.esm-bundler.js"
        }
    },
    module: { 
        rules: [
            {
                test: /\.(m?js|ts?)$/,
                exclude: /node_modules/,
                use: {
                    loader: "babel-loader",
                    options: {
                        presets: [
                            ["@babel/preset-typescript", {}],
                            ["@babel/preset-env", {
                                // debug: true,
                                corejs: { "version": 3 },
                                useBuiltIns: "usage",
                                targets: { 
                                    "firefox": "68",
                                    "chrome": "79",
                                    "edge": "80",
                                    "safari": "13",
                                    "ie": "11"
                                }
                            }]
                        ],
                        plugins: [
                            // Automatically import component JS module and its CSS stylesheet.
                            ["import", {
                                "libraryName": "ant-design-vue",
                                "customName": (name) => `ant-design-vue/es/${name}/index.js`,
                                "style": (name) => `${name}/../style/index.css`
                            }]
                        ]
                    }
                }
            },
            {
                test: /\.vue$/,
                loader: 'vue-loader'
            },
            {
                test: /\.css$/i,
                use: [
                    // Do we need vue-style-loader here instead of style-loader?
                    "style-loader",
                    "css-loader"
                ]
            }
        ]
    },
    plugins: [
        new WebpackAssetsManifest({ entrypoints: true }),
        new CleanWebpackPlugin(),
        new VueLoaderPlugin()
    ],
    output: {
        filename: '[name].js',
        libraryTarget: 'amd',
        path: path.resolve(configRoot, 'dist')
    },
    externals: [
        function({context, request}, callback) {
            // External nextgisweb AMD module from package
            for (const ext of configExternals) {
                if (request.startsWith(ext + '/')) {
                    return callback(null, `amd ${request}`);    
                }
            }
            callback();
        }
    ],
    optimization: {
        splitChunks: {
            chunks: 'all'
        },
    },    
}
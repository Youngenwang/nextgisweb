const path = require('path');
const fs = require('fs');

const WebpackAssetsManifest = require('webpack-assets-manifest');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const { VueLoaderPlugin } = require('vue-loader');

const entryList = {};

const configRoot = process.env.npm_package_config_nextgisweb_jsrealm_root;
const configExternals = process.env.npm_package_config_nextgisweb_jsrealm_external.split(',');
const packageJson = JSON.parse(fs.readFileSync(`${configRoot}/package.json`));

for (const ws of packageJson.workspaces) {
    const subPackageJSON = JSON.parse(fs.readFileSync(`${configRoot}/${ws}/package.json`));
    if ('nextgisweb' in subPackageJSON && 'entrypoints' in subPackageJSON['nextgisweb']) {
        for (const entryFileName of subPackageJSON.nextgisweb.entrypoints) {
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

const stylesheetRoot = path.resolve(__dirname, '../../static');

configStylesheet = {
    mode: 'development',
    devtool: 'source-map',
    entry: {
        'layout': stylesheetRoot + '/css/layout.less',
        'default': stylesheetRoot + '/css/default.css',
        'pure': stylesheetRoot + '/css/pure-0.6.0-min.css'
    },
    output: {
        path: path.resolve(configRoot, 'dist/stylesheet')
    },
    plugins: [
        new CleanWebpackPlugin(),
        new MiniCssExtractPlugin()
    ],
    module: {
        rules: [
            {
                test: /\.less$/,
                use: [
                    {
                        loader: MiniCssExtractPlugin.loader,
                        options: { publicPath: './' }
                    },
                    "css-loader",
                    {
                        loader: 'less-loader',
                        options: {
                            lessOptions: {
                                rootpath: stylesheetRoot + '/css',
                                javascriptEnabled: true,
                            }
                        }
                    }
                ]       
            },
            {
                test: /\.css$/,
                use: [MiniCssExtractPlugin.loader, "css-loader"]
            },
            {
                test: (fp) => fp.startsWith(stylesheetRoot + '/font/'),
                use: [
                    {
                        loader: 'file-loader',
                        options: { outputPath: 'font', name: '[name].[ext]' }
                    }
                ]
            },
            {
                test: (fp) => fp.startsWith(stylesheetRoot + '/svg/'),
                use: [
                    {
                        loader: 'file-loader',
                        options: { outputPath: 'svg', name: '[name].[ext]' }
                    }
                ]
            }

        ]
    }
}


const configMain = {
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
        filename: (pathData) => (
            pathData.chunk.name !== undefined ?
            '[name].js' : 'chunk/[name].js'
        ),
        chunkFilename: 'chunk/[id].js',
        libraryTarget: 'amd',
        path: path.resolve(configRoot, 'dist/main')
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

module.exports = [configMain, configStylesheet]
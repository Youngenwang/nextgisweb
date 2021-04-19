const path = require('path');
const fs = require('fs');

const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const WebpackAssetsManifest = require('webpack-assets-manifest');

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
            const entryFullPath = `${configRoot}/${ws}/${entryFileName}`;
            entryList[`${subPackageJSON.name}/${entryName}`] = entryFullPath;
        }
    }
}

module.exports = {
    mode: 'development',
    devtool: 'source-map',
    entry: entryList,
    module: { 
        rules: [
            {
                test: /\.css$/i,
                use: ["style-loader", "css-loader"]
            }
        ]
    },
    plugins: [
        new WebpackAssetsManifest({ entrypoints: true }),
        new CleanWebpackPlugin()
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
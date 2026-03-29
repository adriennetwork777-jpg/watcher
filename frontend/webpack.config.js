const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

module.exports = {
  mode: 'production',
  entry: './code/index.js',
  output: {
    path: path.resolve(__dirname, 'static/frontend'),
    filename: 'bundle.js',
    publicPath: '/static/frontend/'
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: ['babel-loader']
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx']
  },
  plugins: [
    new CleanWebpackPlugin(),
new HtmlWebpackPlugin({
  template: path.resolve(__dirname, '/static/frontend/index.html')
})
  ]
};
const path = require('path');

module.exports = {
  mode: 'production',
  entry: './code/index.js', // <-- un seul point d'entrée
  output: {
    path: path.resolve(__dirname, 'static/frontend'),
    filename: 'bundle.js'
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: ['babel-loader']
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx']
  }
};
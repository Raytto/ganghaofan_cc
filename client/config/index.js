const ENV = 'development' // 或通过编译时变量确定

const configFiles = {
  development: require('./config.dev.js'),
  production: require('./config.prod.js')
}

const config = configFiles[ENV]

module.exports = config
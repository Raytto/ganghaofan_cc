const ENV = 'development' // 或通过编译时变量确定

const configFiles = {
  development: require('./config.dev.json'),
  production: require('./config.prod.json')
}

const config = configFiles[ENV]

export default config
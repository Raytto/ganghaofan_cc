const ENV = 'development' // 或通过编译时变量确定

const configs = {
  development: () => import('./config.dev.js'),
  production: () => import('./config.prod.js')
}

export default configs[ENV]
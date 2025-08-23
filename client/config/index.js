// 配置管理入口文件
const ENV = 'dev' // 环境标识：dev | prod

const configFiles = {
  'dev': require('./config.dev.js'),
  'prod': require('./config.prod.js')
}

module.exports = configFiles[ENV] || configFiles['dev']
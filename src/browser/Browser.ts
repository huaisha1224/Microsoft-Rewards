import rebrowser, { BrowserContext } from 'patchright'
import { newInjectedContext } from 'fingerprint-injector'
import { BrowserFingerprintWithHeaders, FingerprintGenerator } from 'fingerprint-generator'

import type { MicrosoftRewardsBot } from '../index'
import { loadSession, saveFingerprint } from '../util/SessionStore'
import { fingerprintMatchesLocale } from '../util/Locale'
import { formatBrowserProxyServer } from '../util/Proxy'
import { UserAgentManager } from './UserAgent'
import { URLs } from '../constants/urls'

import type { Account } from '../interface/Account'

/* Test Stuff
https://abrahamjuliot.github.io/creepjs/
https://botcheck.luminati.io/
https://fv.pro/
https://pixelscan.net/
https://www.browserscan.net/
*/

interface BrowserCreationResult {
    context: BrowserContext
    fingerprint: BrowserFingerprintWithHeaders
}

class Browser {
    private readonly bot: MicrosoftRewardsBot
    private readonly fingerprintGenerator = new FingerprintGenerator()
    private readonly userAgentManager: UserAgentManager
    private static readonly BROWSER_ARGS = [
        '--mute-audio',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-web-authentication-ui',
        '--disable-external-intent-requests',
        '--disable-blink-features=AutomationControlled',
        '--disable-features=WebAuthentication,PasswordManagerOnboarding,PasswordManager,EnablePasswordsAccountStorage,Passkeys,WebAuthenticationProxy,U2F',
        '--disable-save-password-bubble',
        '--disable-dev-shm-usage',
        '--disable-background-networking',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding'
    ] as const

    constructor(bot: MicrosoftRewardsBot) {
        this.bot = bot
        this.userAgentManager = new UserAgentManager(bot)
    }

    async createBrowser(account: Account): Promise<BrowserCreationResult> {
        const headless = this.bot.config.headless
        const channel = this.bot.config.browserChannel ?? 'chromium'
        // 真实 Edge 依赖系统安装；linux（docker）环境通常没有，回退内置补丁版 Chromium
        const useRealEdge = channel === 'msedge' && process.platform !== 'linux'
        // 系统 Chrome 同理：直接复用用户机器上已装的正版 Chrome，免去下载内置 Chromium
        const useRealChrome = channel === 'chrome' && process.platform !== 'linux'
        // 二者都是"系统真实浏览器"，共用原生指纹路径（不做合成指纹注入）
        const useSystemBrowser = useRealEdge || useRealChrome

        const hasProxy = Boolean(account.proxy.url)
        const ignoreCertificateErrors = hasProxy && this.bot.config.proxy.ignoreCertificateErrors

        let browser: rebrowser.Browser
        try {
            const proxyConfig = account.proxy.url
                ? {
                      server: formatBrowserProxyServer(account.proxy.url, account.proxy.port),
                      ...(account.proxy.username &&
                          account.proxy.password && {
                              username: account.proxy.username,
                              password: account.proxy.password
                          })
                  }
                : undefined

            const runningAsRoot = typeof process.getuid === 'function' && process.getuid() === 0
            const sandboxDisabled = process.platform === 'linux' && runningAsRoot
            const sandboxArgs = sandboxDisabled ? ['--no-sandbox', '--disable-setuid-sandbox'] : []

            const certArgs = ignoreCertificateErrors
                ? ['--ignore-certificate-errors', '--ignore-certificate-errors-spki-list', '--ignore-ssl-errors']
                : []

            if (ignoreCertificateErrors) {
                this.bot.logger.warn(
                    this.bot.isMobile,
                    'BROWSER-SECURITY',
                    'TLS 证书验证已被 proxy.ignoreCertificateErrors 禁用'
                )
            }

            if (channel === 'msedge' && !useRealEdge) {
                this.bot.logger.warn(
                    this.bot.isMobile,
                    'BROWSER',
                    'browserChannel=msedge 在当前平台不可用（未安装系统 Edge），已回退内置补丁版 Chromium'
                )
            } else if (channel === 'chrome' && !useRealChrome) {
                this.bot.logger.warn(
                    this.bot.isMobile,
                    'BROWSER',
                    'browserChannel=chrome 在当前平台不可用（未安装系统 Chrome），已回退内置补丁版 Chromium'
                )
            } else if (useRealEdge) {
                // Edge 152 + playwright/patchright 1.6x 访问微软账户页面（rewards/登录）会触发浏览器进程崩溃，
                // 上游 issue microsoft/playwright#41438 至 1.63.0 仍未修复；稳定前保持实验性
                this.bot.logger.warn(
                    this.bot.isMobile,
                    'BROWSER',
                    'browserChannel=msedge 为实验性选项：当前 Edge/playwright 版本组合在访问 rewards.bing.com 时可能崩溃（上游 #41438），如遇失败请改回 chromium'
                )
            }

            this.bot.logger.info(
                this.bot.isMobile,
                'BROWSER',
                useSystemBrowser
                    ? `正在启动系统浏览器 (channel=${useRealChrome ? 'chrome' : 'msedge'}) | headless=${headless} | platform=${process.platform} | proxy=${hasProxy ? 'yes' : 'no'} | tls=${ignoreCertificateErrors ? 'verification-disabled' : 'verified'}`
                    : `正在启动内置的补丁版 Chromium (Edge UA) | headless=${headless} | platform=${process.platform} | proxy=${hasProxy ? 'yes' : 'no'} | tls=${ignoreCertificateErrors ? 'verification-disabled' : 'verified'} | sandbox=${sandboxDisabled ? 'disabled-root' : 'enabled'}`
            )

            browser = await rebrowser.chromium.launch({
                headless,
                ...(useRealChrome && { channel: 'chrome' as const }),
                ...(useRealEdge && { channel: 'msedge' as const }),
                ...(proxyConfig && { proxy: proxyConfig }),
                args: [...Browser.BROWSER_ARGS, ...sandboxArgs, ...certArgs]
            })
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error)
            const hint =
                useRealChrome && /not found|Executable doesn't exist|cannot find/i.test(errorMessage)
                    ? '（未检测到系统 Google Chrome：请安装 Chrome，或把 config.json 的 browserChannel 改回 chromium）'
                    : ''
            this.bot.logger.error(this.bot.isMobile, 'BROWSER', `浏览器启动失败: ${errorMessage}${hint}`)
            throw error
        }

        try {
            let session = loadSession(this.bot.config.sessionPath, account.email, this.bot.isMobile)
            let reusedMobileSession = false

            // 桌面会话缺失时，退回使用同账号的移动端会话：
            // 移动端刚登录成功就把 cookie 存了下来，而登录 cookie 与 UA 无关，
            // 直接用可以避免桌面端再次弹密码（账号开了无密码登录时密码根本无效）。
            if (!session?.storageState && !this.bot.isMobile) {
                const mobileFallback = loadSession(this.bot.config.sessionPath, account.email, true)
                if (mobileFallback?.storageState) {
                    session = { ...mobileFallback, fingerprint: null }
                    reusedMobileSession = true
                }
            }

            if (session?.storageState) {
                const ageMinutes = Math.max(0, Math.floor((Date.now() - session.updatedAt) / 60000))
                this.bot.logger.info(
                    this.bot.isMobile,
                    'SESSION',
                    (reusedMobileSession ? '未找到桌面会话，改为复用移动端会话 | ' : '正在恢复已保存的浏览器会话 | ') +
                        `Cookie数=${session.storageState.cookies.length} | origins=${session.storageState.origins.length} | 已保存分钟数=${ageMinutes}` +
                        (session.expiredCookiesRemoved
                            ? ` | 已清除过期Cookie=${session.expiredCookiesRemoved}`
                            : '')
                )
            } else {
                this.bot.logger.info(
                    this.bot.isMobile,
                    'SESSION',
                    `未找到已保存的浏览器会话；可能需要登录 | 邮箱=${account.email} | 平台=${this.bot.isMobile ? 'mobile' : 'desktop'} | 会话目录=${this.bot.config.sessionPath}`
                )
            }

            const shouldUseFingerprint = this.bot.isMobile
                ? account.saveFingerprint.mobile
                : account.saveFingerprint.desktop

            // 系统真实浏览器（Chrome / Edge）桌面端：保留浏览器原生指纹一致性（真 UA/WebGL/字体/编解码器），
            // 不做合成指纹注入，仅从真实环境读取 UA 供 HTTP 层使用
            const useNativeFingerprint = useSystemBrowser && !this.bot.isMobile

            let fingerprint: BrowserFingerprintWithHeaders
            let context: BrowserContext
            let reuseFingerprint: boolean | null | undefined = false

            if (useNativeFingerprint) {
                context = await browser.newContext({
                    permissions: [],
                    ignoreHTTPSErrors: ignoreCertificateErrors,
                    locale: this.bot.accountLocale.locale,
                    viewport: { width: 1920, height: 1080 },
                    // Restore cookies
                    ...(session?.storageState ? { storageState: session.storageState } : {}),
                    // headless 下真 Edge 的 UA 带 HeadlessChrome 标记，用修正后的真实 UA 覆盖
                    ...(headless && { userAgent: await this.resolveNativeUserAgent(browser) })
                })
                fingerprint = await this.captureNativeFingerprint(context)
            } else {
                const savedFingerprint = shouldUseFingerprint ? session?.fingerprint : null
                reuseFingerprint =
                    savedFingerprint && fingerprintMatchesLocale(savedFingerprint, this.bot.accountLocale)

                if (savedFingerprint && !reuseFingerprint) {
                    this.bot.logger.info(
                        this.bot.isMobile,
                        'BROWSER-FINGERPRINT',
                        `已保存的指纹区域与 ${this.bot.accountLocale.locale} 不匹配；正在生成替代指纹`
                    )
                }

                fingerprint =
                    (reuseFingerprint && savedFingerprint) ||
                    (await this.generateFingerprint(this.bot.isMobile))

                const screen = fingerprint.fingerprint.screen

                //@ts-expect-error It doesn't like the browser instance from different packages
                const injected = await newInjectedContext(browser, {
                    fingerprint,
                    newContextOptions: {
                        permissions: [],
                        ignoreHTTPSErrors: ignoreCertificateErrors,
                        // Restore cookies
                        ...(session?.storageState ? { storageState: session.storageState } : {}),
                        ...(this.bot.isMobile
                            ? {
                                  isMobile: true,
                                  hasTouch: true,
                                  deviceScaleFactor: screen.devicePixelRatio,
                                  viewport: { width: screen.width, height: screen.height },
                                  screen: { width: screen.width, height: screen.height }
                              }
                            : {})
                    }
                })
                context = injected as unknown as BrowserContext
            }

            if (hasProxy) {
                await context.addInitScript(() => {
                    // @ts-expect-error Chromium-specific runtime globals
                    delete window.RTCPeerConnection
                    // @ts-expect-error Legacy Chromium runtime global
                    delete window.webkitRTCPeerConnection
                    // @ts-expect-error Chromium-specific runtime global
                    delete window.RTCDataChannel
                })
            }

            context.on('page', p => {
                p.on('crash', () =>
                    this.bot.logger.error(this.bot.isMobile, 'BROWSER', `渲染器崩溃 | ${p.url()}`)
                )
            })
            context.on('close', () => this.bot.logger.warn(this.bot.isMobile, 'BROWSER', '浏览器上下文已关闭'))

            context.setDefaultTimeout(this.bot.utils.stringToNumber(this.bot.config?.globalTimeout ?? 30000))

            if (shouldUseFingerprint && !reuseFingerprint && !useNativeFingerprint) {
                saveFingerprint(this.bot.config.sessionPath, account.email, this.bot.isMobile, fingerprint)
            }

            this.bot.logger.info(
                this.bot.isMobile,
                'BROWSER',
                `已创建上下文 | locale=${this.bot.accountLocale.locale} | Accept-Language="${this.bot.accountLocale.acceptLanguage}" | User-Agent: "${fingerprint.fingerprint.navigator.userAgent}"`
            )
            this.bot.logger.debug(this.bot.isMobile, 'BROWSER-FINGERPRINT', JSON.stringify(fingerprint))

            return { context, fingerprint }
        } catch (error) {
            await browser.close().catch(() => {})
            throw error
        }
    }

    async generateFingerprint(isMobile: boolean): Promise<BrowserFingerprintWithHeaders> {
        const hostOs: 'windows' | 'macos' | 'linux' =
            process.platform === 'darwin' ? 'macos' : process.platform === 'linux' ? 'linux' : 'windows'

        const fingerPrintData = this.fingerprintGenerator.getFingerprint({
            devices: isMobile ? ['mobile'] : ['desktop'],
            operatingSystems: isMobile ? ['android'] : [hostOs],
            browsers: [{ name: 'edge' }],
            locales: this.bot.accountLocale.acceptedLocales
        })

        return this.userAgentManager.updateFingerprintUserAgent(fingerPrintData, isMobile)
    }

    /**
     * headless 下真实 Edge 的 navigator.userAgent 会被标记为 HeadlessChrome。
     * 读取原始值并替换为真实形态（Chrome/{major}.0.0.0 ... Edg/{major}.0.0.0），
     * 供 newContext 显式覆盖 navigator 与 HTTP 头。
     */
    private async resolveNativeUserAgent(browser: rebrowser.Browser): Promise<string> {
        const tempContext = await browser.newContext()
        const page = await tempContext.newPage()
        try {
            const ua = await page.evaluate(() => navigator.userAgent)
            const fixed = ua.replace('HeadlessChrome/', 'Chrome/')
            if (fixed !== ua) {
                this.bot.logger.info(
                    this.bot.isMobile,
                    'BROWSER',
                    '已修正 headless UA 的 HeadlessChrome 标记；WebGL/Client Hints 为真实值无需修正'
                )
            }
            return fixed
        } finally {
            await tempContext.close()
        }
    }

    /**
     * 从真实浏览器环境读取 UA 与 Client Hints，构造 HTTP 层使用的"真指纹"。
     * 仅在真实 Edge 桌面端（不注入合成指纹）时使用。
     */
    private async captureNativeFingerprint(context: BrowserContext): Promise<BrowserFingerprintWithHeaders> {
        const page = await context.newPage()
        try {
            // userAgentData 仅在安全上下文可用，about:blank 读不到，需在真实页面上读取
            await page.goto(URLs.bing.origin, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {})
            const native = await page.evaluate(async () => {
                interface UABrandVersion {
                    brand: string
                    version: string
                }
                interface UAData {
                    brands: Iterable<UABrandVersion>
                    mobile: boolean
                    platform: string
                    getHighEntropyValues(hints: string[]): Promise<{
                        fullVersionList?: UABrandVersion[]
                        platformVersion?: string
                        architecture?: string
                        bitness?: string
                        model?: string
                    }>
                }
                const data = (navigator as Navigator & { userAgentData?: UAData }).userAgentData
                const high = data?.getHighEntropyValues
                    ? await data.getHighEntropyValues([
                          'fullVersionList',
                          'platformVersion',
                          'architecture',
                          'bitness',
                          'model'
                      ])
                    : null
                return {
                    userAgent: navigator.userAgent,
                    language: navigator.language,
                    brands: data ? Array.from(data.brands) : null,
                    mobile: data ? data.mobile : false,
                    platform: data ? data.platform : null,
                    high
                }
            })

            const brandsHeader = native.brands?.map(b => `"${b.brand}";v="${b.version}"`).join(', ')
            const fullVersionList = native.high?.fullVersionList
            const fullHeader = fullVersionList?.map(b => `"${b.brand}";v="${b.version}"`).join(', ')

            return {
                fingerprint: {
                    navigator: {
                        userAgent: native.userAgent,
                        language: native.language
                    },
                    screen: { width: 1920, height: 1080, devicePixelRatio: 1 }
                },
                headers: {
                    'user-agent': native.userAgent,
                    'accept-language': this.bot.accountLocale.acceptLanguage,
                    ...(brandsHeader && { 'sec-ch-ua': brandsHeader }),
                    ...(fullHeader && { 'sec-ch-ua-full-version-list': fullHeader }),
                    'sec-ch-ua-mobile': native.mobile ? '?1' : '?0',
                    ...(native.platform && { 'sec-ch-ua-platform': `"${native.platform}"` })
                }
            } as unknown as BrowserFingerprintWithHeaders
        } finally {
            await page.close()
        }
    }
}

export default Browser

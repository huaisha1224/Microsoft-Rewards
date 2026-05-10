// ==UserScript==
// @name         Microsoft Bing Rewards每日任务脚本
// @version      V5.1.0
// @description  自动打开Microsoft Rewards页面、点击每日活动、执行搜索任务、每次运行时获取抖音/微博/哔哩哔哩/百度/头条热门词,避免使用同样的搜索词被封号。
// @author       怀沙2049
// @match        *://cn.bing.com/*
// @match        *://www.bing.com/*
// @match        *://bing.com/*
// @match        *://rewards.bing.com/*
// @run-at       document-idle
// @grant        GM_registerMenuCommand
// @icon         https://www.bing.com/favicon.ico
// @connect      gumengya.com
// @run-at       document-end
// @grant        GM_registerMenuCommand
// @grant        GM_addStyle
// @grant        GM_openInTab
// @grant        GM_setValue
// @grant        GM_getValue
// @license      GNU GPLv3
// @grant        GM_xmlhttpRequest
// @namespace    https://greasyfork.org/zh-CN/scripts/477107
// @downloadURL https://update.greasyfork.org/scripts/477107/Microsoft%20Bing%20Rewards%E6%AF%8F%E6%97%A5%E4%BB%BB%E5%8A%A1%E8%84%9A%E6%9C%AC.user.js
// @updateURL https://update.greasyfork.org/scripts/477107/Microsoft%20Bing%20Rewards%E6%AF%8F%E6%97%A5%E4%BB%BB%E5%8A%A1%E8%84%9A%E6%9C%AC.meta.js
// ==/UserScript==

(function() {
    'use strict';
    console.log('=== Microsoft Rewards 完整版脚本开始运行 ===');
    console.log('当前页面:', window.location.href);
    console.log('当前域名:', window.location.hostname);

    // ==================== 配置参数 ====================
    const REWARDS_URL = 'https://rewards.bing.com/dashboard';
    const MAX_SEARCH_REWARDS = 25; // 最大搜索次数
    //每执行4次搜索后插入暂停时间,解决账号被监控不增加积分的问题
    const PAUSE_TIME = GM_getValue('ms_rewards_pause_time', 6); // 如果有问题可以修改这里的暂停时长，建议16分钟,也就是960000(60000毫秒=1分钟)
    const REWARDS_COOLDOWN = 1800000; // rewards页面冷却时间（30分钟）
    
    // API Key配置
    //从https://www.gmya.net/api 网站申请的热门词接口APIKEY
    let appkey = GM_getValue('ms_rewards_appkey', ''); // 这里输入你的API Key

    // ==================== 搜索任务配置 ====================
    let search_words = [];
    const default_search_words = ["盛年不重来，一日难再晨", "千里之行，始于足下", "少年易学老难成，一寸光阴不可轻", "敏而好学，不耻下问", "海内存知已，天涯若比邻", "三人行，必有我师焉",
    "莫愁前路无知已，天下谁人不识君", "人生贵相知，何用金与钱", "天生我材必有用", "海纳百川有容乃大；壁立千仞无欲则刚", "穷则独善其身，达则兼济天下", "读书破万卷，下笔如有神",
    "学而不思则罔，思而不学则殆", "一年之计在于春，一日之计在于晨", "莫等闲，白了少年头，空悲切", "少壮不努力，老大徒伤悲", "一寸光阴一寸金，寸金难买寸光阴", "近朱者赤，近墨者黑",
    "吾生也有涯，而知也无涯", "纸上得来终觉浅，绝知此事要躬行", "学无止境", "己所不欲，勿施于人", "天将降大任于斯人也", "鞠躬尽瘁，死而后已", "书到用时方恨少", "天下兴亡，匹夫有责",
    "人无远虑，必有近忧", "为中华之崛起而读书", "一日无书，百事荒废", "岂能尽如人意，但求无愧我心", "人生自古谁无死，留取丹心照汗青", "吾生也有涯，而知也无涯", "生于忧患，死于安乐"]

    //{weibohot}微博热搜榜/{bilihot}哔哩热搜榜/{douyinhot}抖音热搜榜/{zhihuhot}知乎热搜榜/{baiduhot}百度热搜榜
    const keywords_source = ['ZhiHuHot', 'WeiBoHot', 'TouTiaoHot', 'DouYinHot', 'BaiduHot'];
    const random_keywords_source = keywords_source[Math.floor(Math.random() * keywords_source.length)];
    const Hot_words_apis = "https://api.gmya.net/Api/";

    // ==================== 获取热门搜索词 ====================
    function getHotWords() {
        let url = Hot_words_apis + random_keywords_source;
        if (appkey) {
            url += '?format=json&appkey=' + appkey;
        } else {
            url += '?format=json';
        }
        console.log('尝试获取热门搜索词，URL:', url);
        return new Promise((resolve, reject) => {
            fetch(url)
                .then(response => {
                    console.log('API响应状态:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('API返回数据:', JSON.stringify(data));
                    if (data.data && data.data.some(item => item)) {
                        const names = data.data.map(item => item.title);
                        console.log('获取到的热门搜索词:', names);
                        resolve(names);
                    } else {
                        console.log('API返回数据格式不正确，使用默认搜索词');
                        resolve(default_search_words);
                    }
                })
                .catch(error => {
                    console.error('获取热门搜索词失败:', error);
                    resolve(default_search_words);
                });
        });
    }

    // ==================== 生成随机字符串 ====================
    function generateRandomString(length) {
        const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += characters.charAt(Math.floor(Math.random() * characters.length));
        }
        return result;
    }

    // ==================== 平滑滚动到页面底部 ====================
    function smoothScrollToBottom() {
        document.documentElement.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }

    // ==================== 搜索任务执行函数 ====================
    function executeSearchTask() {
        let randomDelay = Math.floor(Math.random() * 60000) + 20000; // 10-30秒随机延迟
        let randomString = generateRandomString(4);
        let randomCvid = generateRandomString(32);

        if (GM_getValue('search_cnt') == null) {
            GM_setValue('search_cnt', 0);
        }

        let currentSearchCount = GM_getValue('search_cnt');

        if (currentSearchCount < MAX_SEARCH_REWARDS) {
            let tt = document.getElementsByTagName("title")[0];
            tt.innerHTML = "[" + (currentSearchCount + 1) + " / " + MAX_SEARCH_REWARDS + "] " + tt.innerHTML;
            smoothScrollToBottom();
            GM_setValue('search_cnt', currentSearchCount + 1);

            setTimeout(function() {
                let nowtxt = search_words[currentSearchCount % search_words.length];
                let searchUrl = "https://www.bing.com/search?q=" + encodeURI(nowtxt) + "&form=" + randomString + "&cvid=" + randomCvid;

                if ((currentSearchCount + 1) % 5 === 0) {
                    setTimeout(function() {
                        location.href = searchUrl;
                    }, PAUSE_TIME);
                } else {
                    location.href = searchUrl;
                }
            }, randomDelay);
        } else {
            console.log('✅ 搜索任务已完成');
            GM_setValue('search_completed', 'true');
            // 搜索任务完成后，直接打开rewards页面
            setTimeout(() => {
                console.log('搜索任务完成，准备打开rewards页面...');
                
                const REWARDS_OPENED_AFTER_SEARCH = 'ms_rewards_opened_after_search';
                
                // 检查是否已经打开过
                const sessionOpened = sessionStorage.getItem(REWARDS_OPENED_AFTER_SEARCH);
                if (sessionOpened === 'true') {
                    console.log('⚠️ 已打开过 rewards 页面，跳过');
                    return;
                }
                
                // 设置标记
                sessionStorage.setItem(REWARDS_OPENED_AFTER_SEARCH, 'true');
                localStorage.setItem(REWARDS_OPENED_AFTER_SEARCH, 'true');
                
                // 打开 rewards 页面
                const rewardsUrlWithFlag = REWARDS_URL + '?auto_opened=true&timestamp=' + Date.now();
                window.open(rewardsUrlWithFlag, '_blank');
                console.log('✓ 已打开 rewards 页面');
                
                // 重置搜索完成标记
                GM_setValue('search_completed', 'false');
                
                // 10分钟后清除 localStorage 备份
                setTimeout(() => {
                    localStorage.removeItem(REWARDS_OPENED_AFTER_SEARCH);
                }, 600000);
            }, 3000);
        }
    }

    // ==================== Rewards页面功能 ====================
    function handleRewardsPage() {
        console.log('✓ 已在rewards页面，开始查找每日活动...');
        console.log('当前URL:', window.location.href);
        
        // 检查是否已经执行过每日活动点击
        const REWARDS_ACTIVITY_CLICKED_KEY = 'ms_rewards_activity_clicked';
        const activityClicked = localStorage.getItem(REWARDS_ACTIVITY_CLICKED_KEY);
        const now = Date.now();
        
        // 检查 URL 中是否有自动打开的标记（说明是从搜索任务跳转过来的）
        const urlParams = new URLSearchParams(window.location.search);
        const isAutoOpened = urlParams.get('auto_opened') === 'true';
        
        console.log('每日活动标记状态:', activityClicked ? '已设置' : '未设置');
        console.log('是否自动打开:', isAutoOpened ? '是' : '否');
        
        if (isAutoOpened) {
            console.log('🔄 检测到这是从搜索任务自动打开的，清除旧的每日活动标记');
            // 清除旧的标记，允许重新执行每日活动
            localStorage.removeItem(REWARDS_ACTIVITY_CLICKED_KEY);
        }
        
        // 如果今天已经执行过，则不再重复执行
        if (activityClicked && !isAutoOpened) {
            const clickTime = parseInt(activityClicked);
            const today = new Date();
            const lastClickDate = new Date(clickTime);
            
            // 检查是否是同一天
            if (today.toDateString() === lastClickDate.toDateString()) {
                console.log('✅ 今日已执行过每日活动点击，跳过');
                console.log('上次执行时间:', lastClickDate.toLocaleString());
                return;
            } else {
                console.log('📅 检测到是新的一天，清除旧标记');
                // 新的一天，清除标记
                localStorage.removeItem(REWARDS_ACTIVITY_CLICKED_KEY);
            }
        }
        
        // 注意：不要在这里清除任何标记！
        console.log('✅ 准备执行每日活动点击');

        setTimeout(() => {
            console.log('开始查找每日活动...');

            const allLinks = document.querySelectorAll('a');
            console.log('找到的所有链接数量:', allLinks.length);

            const potentialActivityLinks = [];
            allLinks.forEach((link, index) => {
                const href = link.href;
                const text = link.textContent;

                if (href.includes('/search') || href.includes('quiz') || href.includes('poll') || 
                    href.includes('challenge') || href.includes('activity') || 
                    text.includes('活动') || text.includes('任务') || text.includes('积分') ||
                    text.includes('喜剧') || text.includes('鲸鱼') || text.includes('美食')) {
                    potentialActivityLinks.push(link);
                    console.log(`找到潜在活动链接 ${potentialActivityLinks.length}:`, href, text.substring(0, 30));
                }
            });

            console.log('找到的潜在活动链接数量:', potentialActivityLinks.length);

            const xpathLinks = [];
            try {
                const xpathExpressions = [
                    '//*[contains(@id, "react-aria") and contains(@id, "_r_2_")]//a[1]',
                    '//*[contains(@id, "react-aria") and contains(@id, "_r_2_")]//a[2]',
                    '//*[contains(@id, "react-aria") and contains(@id, "_r_2_")]//a[3]'
                ];

                xpathExpressions.forEach((xpath, index) => {
                    const element = document.evaluate(
                        xpath,
                        document,
                        null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                        null
                    ).singleNodeValue;

                    if (element) {
                        xpathLinks.push(element);
                        console.log(`通过XPath找到链接 ${xpathLinks.length}:`, element.href);
                    }
                });
            } catch (e) {
                console.log('XPath查找出错:', e);
            }

            console.log('通过XPath找到的链接数量:', xpathLinks.length);

            let linksToClick = [];
            if (xpathLinks.length > 0) {
                linksToClick = xpathLinks.slice(0, 3);
                console.log('优先使用XPath找到的链接');
            } else {
                const dailyActivityLinks = potentialActivityLinks.filter(link => {
                    const href = link.href;
                    const text = link.textContent;

                    if (href.includes('/refer') || text.includes('邀请好友') || 
                        href.includes('/dashboard') || href.includes('/home')) {
                        return false;
                    }

                    return href.includes('/search') || href.includes('quiz') || 
                           href.includes('poll') || href.includes('challenge') || 
                           href.includes('activity') || text.includes('活动') || 
                           text.includes('任务') || text.includes('积分');
                });

                linksToClick = dailyActivityLinks.slice(0, 3);
                console.log('使用过滤后的每日活动链接');
            }

            console.log('准备点击的链接数量:', linksToClick.length);

            if (linksToClick.length === 0) {
                console.log('⚠️ 没有找到可点击的每日活动链接');
                // 即使没有链接，也标记为已执行，避免无限循环
                localStorage.setItem(REWARDS_ACTIVITY_CLICKED_KEY, now.toString());
                return;
            }

            linksToClick.forEach((link, index) => {
                setTimeout(() => {
                    console.log(`点击第 ${index+1} 个每日活动链接:`, link.href);
                    
                    // 设置标记，表示这是每日活动的搜索，不是主搜索任务
                    GM_setValue('is_daily_activity', 'true');
                    
                    // 如果是最后一个链接，设置执行标记
                    if (index === linksToClick.length - 1) {
                        localStorage.setItem(REWARDS_ACTIVITY_CLICKED_KEY, Date.now().toString());
                        console.log('✅ 已设置今日执行标记，避免重复执行');
                    }
                    
                    link.click();
                }, index * 1500);
            });

        }, 5000);
    }

    // ==================== Bing主页功能 ====================
    function handleBingHomePage() {
        console.log('⚠ 在bing.com主页');
        
        // 检查是否是从菜单点击“开始搜索任务”跳转过来的
        const urlParams = new URLSearchParams(window.location.search);
        const isStartSearch = urlParams.get('start_search') === 'true';
        
        // 如果是，则立即跳转到第一个搜索
        if (isStartSearch) {
            console.log('🚀 检测到开始搜索任务指令，准备开始搜索...');
            setTimeout(() => {
                const randomString = generateRandomString(4);
                const randomCvid = generateRandomString(32);
                const firstSearchWord = search_words[0] || 'Microsoft Rewards';
                location.href = `https://www.bing.com/search?q=${encodeURI(firstSearchWord)}&form=${randomString}&cvid=${randomCvid}`;
            }, 1000);
            return;
        }
        
        // 检查搜索任务是否已完成
        const searchCompleted = GM_getValue('search_completed');
        
        // ✅ 新增：检查是否已经自动打开过 rewards 页面（会话级别）
        const AUTO_OPENED_KEY = 'ms_rewards_auto_opened_session';
        const alreadyOpened = sessionStorage.getItem(AUTO_OPENED_KEY);
        
        // 只有在明确标记为搜索完成且未打开过时才打开 rewards
        if (searchCompleted === 'true' && alreadyOpened !== 'true') {
            console.log('✅ 搜索任务已完成，准备打开rewards页面...');
            
            const REWARDS_OPENED_AFTER_SEARCH = 'ms_rewards_opened_after_search';

            // ✅ 首先检查会话级别标记（本次会话是否已自动打开）
            const sessionAutoOpened = sessionStorage.getItem(AUTO_OPENED_KEY);
            if (sessionAutoOpened === 'true') {
                console.log('⚠️ 本次会话已自动打开过 rewards 页面，跳过');
                return;
            }

            // 其次检查 sessionStorage 标记（最高优先级）
            const sessionOpened = sessionStorage.getItem(REWARDS_OPENED_AFTER_SEARCH);
            if (sessionOpened === 'true') {
                console.log('⚠️ sessionStorage 显示已打开过 rewards 页面，跳过');
                return;
            }
            
            // 其次检查 localStorage 备份标记
            const localOpened = localStorage.getItem(REWARDS_OPENED_AFTER_SEARCH);
            if (localOpened === 'true') {
                console.log('⚠️ localStorage 备份显示已打开过 rewards 页面，跳过');
                return;
            }

            // 尝试打开 rewards 页面
            try {
                console.log('尝试打开rewards页面...');
                // 添加特殊参数标记这是脚本自动打开的
                const now = Date.now();
                const rewardsUrlWithFlag = REWARDS_URL + '?auto_opened=true&timestamp=' + now;
                const newWindow = window.open(rewardsUrlWithFlag, '_blank');
                if (newWindow) {
                    console.log('✓ 已成功打开rewards页面');
                    
                    // ✅ 设置会话标记，防止再次自动打开
                    sessionStorage.setItem(AUTO_OPENED_KEY, 'true');
                    sessionStorage.setItem(REWARDS_OPENED_AFTER_SEARCH, 'true');
                    localStorage.setItem(REWARDS_OPENED_AFTER_SEARCH, 'true');
                    
                    // ✅ 重置搜索完成标记，防止下次打开 Bing 首页时再次跳转
                    GM_setValue('search_completed', 'false');
                } else {
                    console.log('✗ 无法打开新窗口，可能被浏览器阻止');
                    console.log('提示：请允许弹出窗口，或手动访问 rewards.bing.com');
                }
            } catch (e) {
                console.log('✗ 打开页面时出错:', e);
            }
        } else {
            if (alreadyOpened === 'true') {
                console.log('⚠ 本次会话已自动打开过 rewards 页面，不再重复打开');
            } else {
                console.log('⚠ 搜索任务未完成，不自动打开rewards页面');
            }
        }
    }

    // ==================== 搜索页面功能 ====================
    function handleSearchPage() {
        console.log('⚠ 在搜索页面');
        
        // 检查是否是每日活动的搜索
        const isDailyActivity = GM_getValue('is_daily_activity');
        
        if (isDailyActivity === 'true') {
            console.log('✅ 这是每日活动的搜索，不执行主搜索任务');
            // 清除标记
            GM_setValue('is_daily_activity', 'false');
            return;
        }
        
        console.log('⚠ 执行主搜索任务');
        executeSearchTask();
    }

    // ==================== 主逻辑 ====================
    function main() {
        if (window.location.hostname === 'rewards.bing.com') {
            handleRewardsPage();
        } else if (window.location.href.includes('/search') || window.location.href.includes('br_msg=Please-Wait')) {
            handleSearchPage();
        } else if (window.location.hostname === 'cn.bing.com' || window.location.hostname === 'www.bing.com' || window.location.hostname === 'bing.com') {
            handleBingHomePage();
        } else {
            console.log('⚠ 不在目标域名，脚本不执行');
        }
    }

    // ==================== 菜单命令 ====================
    GM_registerMenuCommand('开始搜索任务', function() {
        GM_setValue('search_cnt', 0);
        GM_setValue('search_completed', 'false');
        // 清除每日活动标记
        GM_setValue('is_daily_activity', 'false');
        // 跳转到 Bing 首页，然后会自动开始搜索任务
        location.href = "https://www.bing.com/?start_search=true";
        console.log('✅ 搜索任务已开始');
    }, 's');

    GM_registerMenuCommand('停止搜索任务', function() {
        GM_setValue('search_cnt', MAX_SEARCH_REWARDS + 10);
        console.log('✅ 搜索任务已停止');
    }, 't');

    // GM_registerMenuCommand('开始任务', function() {
    //     // 清除每日活动标记，允许重新执行
    //     localStorage.removeItem('ms_rewards_activity_clicked');
    //     // 清除打开标记，允许打开 rewards 页面
    //     sessionStorage.removeItem('ms_rewards_opened_after_search');
    //     localStorage.removeItem('ms_rewards_opened_after_search');
    //     // 添加特殊参数标记
    //     const rewardsUrlWithFlag = REWARDS_URL + '?auto_opened=true&timestamp=' + Date.now();
    //     window.open(rewardsUrlWithFlag, '_blank');
    //     console.log('✅ 已打开Rewards页面，并清除旧的活动标记');
    // }, 'r');

    // GM_registerMenuCommand('停止任务', function() {
    //     GM_setValue('search_cnt', MAX_SEARCH_REWARDS + 10);
    //     console.log('✅ 搜索任务已停止');
    // }, 't');

    // GM_registerMenuCommand('清除Rewards冷却', function() {
    //     localStorage.removeItem('ms_rewards_opened');
    //     localStorage.removeItem('ms_rewards_last_opened');
    //     console.log('✅ 已清除Rewards冷却标记');
    // }, 'c');

    GM_registerMenuCommand('设置API Key', function() {
        const key = prompt('请输入API Key:', appkey);
        if (key !== null) {
            GM_setValue('ms_rewards_appkey', key);
            appkey = key;
            console.log('✅ API Key已设置');
        }
    }, 'k');

    // GM_registerMenuCommand('查看当前API Key', function() {
    //     alert('当前API Key: ' + (appkey || '未设置'));
    //     console.log('当前API Key:', appkey || '未设置');
    // }, 'v');


    GM_registerMenuCommand('申请API Key', function() {
        window.open('https://www.gmya.net/api', '_blank');
        console.log('✅ 已打开API申请页面');
    }, 'a');

    GM_registerMenuCommand('清除今日执行标记', function() {
        localStorage.removeItem('ms_rewards_activity_clicked');
        localStorage.removeItem('ms_rewards_opened_after_search');
        sessionStorage.removeItem('ms_rewards_opened_after_search');
        sessionStorage.removeItem('ms_rewards_auto_opened_session'); // ✅ 新增：清除会话标记
        localStorage.removeItem('ms_rewards_opened');
        localStorage.removeItem('ms_rewards_last_opened');
        GM_setValue('search_completed', 'false');
        GM_setValue('search_cnt', 0);
        console.log('✅ 已清除所有执行标记，可以重新执行任务');
        alert('已清除所有执行标记\n刷新页面后可以重新执行每日活动');
    }, 'x');

    // ==================== 初始化 ====================
    getHotWords().then(names => {
        search_words = names;
        console.log('✅ 已获取搜索词，数量:', search_words.length);
        main();
    }).catch(error => {
        console.error('获取搜索词失败:', error);
        search_words = default_search_words;
        main();
    });

    console.log('=== 脚本初始化完成 ===');
})();
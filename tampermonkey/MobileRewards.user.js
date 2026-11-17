// ==UserScript==
// @name         移动端微软Rewards每日任务脚本
// @version      2026.2.2.1
// @description  盒马卡，加油卡，电影卡，天猫卡，山姆卡通通都有（已加：运行完成弹提示）
// @author       怀沙2049
// @match        https://*.bing.com/*
// @license      GNU GPLv3
// @icon         https://www.bing.com/favicon.ico
// @connect      gumengya.com
// @run-at       document-end
// @note         更新于 2026年2月2日；2026.2.2.1 增加运行完成提示
// @supportURL   https://greasyfork.org/zh-CN/users/1192640-huaisha1224
// @homepageURL  https://greasyfork.org/zh-CN/users/1192640-huaisha1224
// @grant        GM_registerMenuCommand
// @grant        GM_addStyle
// @grant        GM_openInTab
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @grant        GM_notification
// @namespace    https://greasyfork.org/zh-CN/users/1192640-huaisha1224
// @downloadURL https://update.greasyfork.org/scripts/480355/%E7%A7%BB%E5%8A%A8%E7%AB%AF%E5%BE%AE%E8%BD%AFRewards%E6%AF%8F%E6%97%A5%E4%BB%BB%E5%8A%A1%E8%84%9A%E6%9C%AC.user.js
// @updateURL https://update.greasyfork.org/scripts/480355/%E7%A7%BB%E5%8A%A8%E7%AB%AF%E5%BE%AE%E8%BD%AFRewards%E6%AF%8F%E6%97%A5%E4%BB%BB%E5%8A%A1%E8%84%9A%E6%9C%AC.meta.js
// ==/UserScript==

var max_rewards = 25; //重复执行的次数
//每执行4次搜索后插入暂停时间,解决账号被监控不增加积分的问题
var pause_time = 9; // 暂停时长建议为16分钟,也就是960000(60000毫秒=1分钟)
var search_words = []; //搜索词
var appkey = "";// 从https://www.gmya.net/api 网站申请的热门词接口APIKEY
var Hot_words_apis = "https://api.gmya.net/Api/";// 故梦热门词API接口网站


var default_search_words = ["盛年不重来，一日难再晨", "千里之行，始于足下", "少年易学老难成，一寸光阴不可轻", "敏而好学，不耻下问", "海内存知已，天涯若比邻", "三人行，必有我师焉",
    "莫愁前路无知已，天下谁人不识君", "人生贵相知，何用金与钱", "天生我材必有用", "海纳百川有容乃大；壁立千仞无欲则刚", "穷则独善其身，达则兼济天下", "读书破万卷，下笔如有神",
    "学而不思则罔，思而不学则殆", "一年之计在于春，一日之计在于晨", "莫等闲，白了少年头，空悲切", "少壮不努力，老大徒伤悲", "一寸光阴一寸金，寸金难买寸光阴", "近朱者赤，近墨者黑",
    "吾生也有涯，而知也无涯", "纸上得来终觉浅，绝知此事要躬行", "学无止境", "己所不欲，勿施于人", "天将降大任于斯人也", "鞠躬尽瘁，死而后已", "书到用时方恨少", "天下兴亡，匹夫有责",
    "人无远虑，必有近忧", "为中华之崛起而读书", "一日无书，百事荒废", "岂能尽如人意，但求无愧我心", "人生自古谁无死，留取丹心照汗青", "吾生也有涯，而知也无涯", "生于忧患，死于安乐"]
//{weibohot}微博热搜榜/{bilihot}哔哩热搜榜/{douyinhot}抖音热搜榜/{zhihuhot}知乎热搜榜/{baiduhot}百度热搜榜

var keywords_source = ['DouYinHot','BaiduHot','ZhiHuHot','WeiBoHot','TouTiaoHot'];
var random_keywords_source = keywords_source[Math.floor(Math.random() * keywords_source.length)]
//每次运行时随机获取一个热门搜索词来源用来作为关键词
function douyinhot_dic() {
    // 根据 appkey 是否为空来决定如何构建 URL 地址
    let url;
    if (appkey) {
        url = Hot_words_apis + random_keywords_source + "?format=json&appkey=" + appkey; // 有 appkey 则添加 appkey 参数
    } else {
        url = Hot_words_apis + random_keywords_source; // 无 appkey 则直接请求接口地址
    }
    return new Promise((resolve, reject) => {
        // 发送GET请求到指定URL
        fetch(url)
            .then(response => response.json()) // 将返回的响应转换为JSON格式
            .then(data => {
                if (data.data.some(item => item)) {
                    // 提取每个元素的name属性值
                    const names = data.data.map(item => item.title);
                    resolve(names); // 将name属性值作为Promise对象的结果返回
                } else {
                    //如果为空使用默认搜索词
                    resolve(default_search_words)
                }
            })
            .catch(error => {
                // 如果请求失败，则返回默认搜索词
                resolve(default_search_words)
                reject(error); // 将错误信息作为Promise对象的错误返回
            });
    });
}


// ==================== 运行完成提示 ====================
// 在页面中间弹出一个大号提示卡片，同时尝试系统通知和震动（手机端更容易注意到）
function showFinishTip(titleText, detailText) {
    try {
        var old = document.getElementById('mr-finish-tip');
        if (old && old.parentNode) old.parentNode.removeChild(old);

        var box = document.createElement('div');
        box.id = 'mr-finish-tip';
        box.style.cssText = [
            'position:fixed',
            'left:14px',
            'right:14px',
            'top:20%',
            'z-index:2147483647',
            'box-sizing:border-box',
            'padding:20px 18px 16px',
            'border-radius:16px',
            'background:rgba(28,28,30,0.97)',
            'color:#ffffff',
            'box-shadow:0 12px 36px rgba(0,0,0,0.5)',
            'font:15px/1.6 -apple-system,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif',
            'text-align:center',
            'border:1px solid rgba(255,255,255,0.18)',
            'word-break:break-all'
        ].join(';');

        var h = document.createElement('div');
        h.textContent = titleText;
        h.style.cssText = 'font-size:19px;font-weight:700;margin-bottom:8px;line-height:1.4';

        var p = document.createElement('div');
        p.textContent = detailText;
        p.style.cssText = 'opacity:0.86;font-size:14px;margin-bottom:16px;line-height:1.6';

        var btn = document.createElement('button');
        btn.textContent = '知道了';
        btn.style.cssText = [
            'display:inline-block',
            'padding:9px 34px',
            'border:0',
            'border-radius:999px',
            'background:#0a84ff',
            'color:#fff',
            'font-size:15px',
            'font-weight:600',
            'cursor:pointer'
        ].join(';');
        btn.onclick = function () {
            if (box.parentNode) box.parentNode.removeChild(box);
        };

        box.appendChild(h);
        box.appendChild(p);
        box.appendChild(btn);
        (document.body || document.documentElement).appendChild(box);

        // 10 秒后自动收起（点“知道了”则立即收起）
        setTimeout(function () {
            if (box.parentNode) box.parentNode.removeChild(box);
        }, 10000);

        // 手机震动：两短一长，容易察觉
        try {
            if (navigator.vibrate) navigator.vibrate([300, 120, 300, 120, 500]);
        } catch (e) { /* 忽略 */ }

        // 系统通知（Tampermonkey 支持且系统授权时才生效，失败不影响页面提示）
        try {
            if (typeof GM_notification === 'function') {
                GM_notification({
                    title: titleText,
                    text: detailText,
                    timeout: 10000
                });
            }
        } catch (e) { /* 忽略 */ }
    } catch (e) {
        console.error('[Rewards] 完成提示显示失败', e);
    }
}

// 任务跑完（或被手动停止）时调用；同一次运行只会提示一次
function notifyTaskEnd(count) {
    var stopped = GM_getValue('Stopped') ? true : false;
    var done = stopped ? (GM_getValue('StoppedAt') || 0) : count;

    if (stopped) {
        showFinishTip('⏸ 任务已手动停止', '本次已完成 ' + done + ' / ' + max_rewards + ' 次搜索，下次可重新点“开始”。');
    } else {
        showFinishTip('✅ 今日搜索任务已完成', '本次已完成 ' + count + ' / ' + max_rewards + ' 次搜索，可以回 Rewards 页面看看积分了。');
    }
}


// 调用douyinhot_dic函数，获取names列表
douyinhot_dic()
    .then(names => {
        //   console.log(names[0]);
        search_words = names;
        exec()
    })
    .catch(error => {
        console.error(error);
    });

// 定义菜单命令：开始
let menu1 = GM_registerMenuCommand('开始', function () {
    GM_setValue('Cnt', 0); // 将计数器重置为0
    GM_setValue('Running', 1); // 标记“本次任务正在进行”
    GM_setValue('Stopped', 0); // 清除上次的停止标记
    GM_setValue('StoppedAt', 0);
    location.href = "https://www.bing.com/?br_msg=Please-Wait"; // 跳转到Bing首页
}, 'o');

// 定义菜单命令：停止
let menu2 = GM_registerMenuCommand('停止', function () {
    GM_setValue('Stopped', 1); // 标记为手动停止
    GM_setValue('StoppedAt', GM_getValue('Cnt') || 0); // 记录停止时已完成的次数
    GM_setValue('Cnt', max_rewards + 10); // 将计数器设置为超过最大搜索次数，以停止搜索
}, 'o');


// 生成指定长度的包含大写字母、数字的随机字符串
function generateRandomString(length) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    const charactersLength = characters.length;
    for (let i = 0; i < length; i++) {
        // 从字符集中随机选择字符，并拼接到结果字符串中
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
}

function exec() {
    // 生成随机延迟时间
    let randomDelay = Math.floor(Math.random() * 20000) + 10000; // 生成10秒到30秒之间的随机数
    let randomString = generateRandomString(4); //生成4个长度的随机字符串
    let randomCvid = generateRandomString(32); //生成32位长度的cvid
    'use strict';

    // 检查计数器的值，若为空则设置为超过最大搜索次数（首次安装/未点开始时保持空闲，不弹提示）
    if (GM_getValue('Cnt') == null) {
        GM_setValue('Cnt', max_rewards + 10);
        GM_setValue('Running', 0);
    }

    // 获取当前搜索次数
    let currentSearchCount = GM_getValue('Cnt');

    // ===== 任务结束判定：跑满次数或被手动停止，弹出提示后不再搜索 =====
    if (currentSearchCount >= max_rewards) {
        if (GM_getValue('Running')) {
            GM_setValue('Running', 0); // 只提示一次，避免刷新页面反复弹
            // 稍等一会儿再弹，避免页面还在跳转时提示被冲掉
            setTimeout(function () {
                notifyTaskEnd(max_rewards);
            }, 800);
        }
        return;
    }

    // 根据计数器的值选择搜索引擎
    if (currentSearchCount <= max_rewards / 2) {
        let tt = document.getElementsByTagName("title")[0];
        tt.innerHTML = "[" + currentSearchCount + " / " + max_rewards + "] " + tt.innerHTML; // 在标题中显示当前搜索次数
        smoothScrollToBottom(); // 添加执行滚动页面到底部的操作
        GM_setValue('Cnt', currentSearchCount + 1); // 将计数器加1
        setTimeout(function () {
            let nowtxt = search_words[currentSearchCount]; // 获取当前搜索词

            // 检查是否需要暂停
            if ((currentSearchCount + 1) % 5 === 0) {
                // 暂停指定时长
                setTimeout(function() {
                    location.href = "https://www.bing.com/search?q=" + encodeURI(nowtxt) + "&form=" + randomString + "&cvid=" + randomCvid; // 在Bing搜索引擎中搜索
                }, pause_time);
            } else {
                location.href = "https://www.bing.com/search?q=" + encodeURI(nowtxt) + "&form=" + randomString + "&cvid=" + randomCvid; // 在Bing搜索引擎中搜索
            }
        }, randomDelay);
    } else if (currentSearchCount > max_rewards / 2 && currentSearchCount < max_rewards) {
        let tt = document.getElementsByTagName("title")[0];
        tt.innerHTML = "[" + currentSearchCount + " / " + max_rewards + "] " + tt.innerHTML; // 在标题中显示当前搜索次数
        smoothScrollToBottom(); // 添加执行滚动页面到底部的操作
        GM_setValue('Cnt', currentSearchCount + 1); // 将计数器加1
        setTimeout(function () {
            let nowtxt = search_words[currentSearchCount]; // 获取当前搜索词

            // 检查是否需要暂停
            if ((currentSearchCount + 1) % 5 === 0) {
                // 暂停指定时长
                setTimeout(function() {
                    location.href = "https://cn.bing.com/search?q=" + encodeURI(nowtxt) + "&form=" + randomString + "&cvid=" + randomCvid; // 在Bing搜索引擎中搜索
                }, pause_time);
            } else {
                location.href = "https://cn.bing.com/search?q=" + encodeURI(nowtxt) + "&form=" + randomString + "&cvid=" + randomCvid; // 在Bing搜索引擎中搜索
            }
        }, randomDelay);
    }
        // 实现平滑滚动到页面底部的函数
    function smoothScrollToBottom() {
            document.documentElement.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
}

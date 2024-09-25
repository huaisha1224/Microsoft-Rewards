// ==UserScript==
// @name         移动端微软Rewards每日任务脚本
// @version      2024.9.10
// @description  盒马卡，加油卡，电影卡，天猫卡，山姆卡通通都有
// @author       怀沙2049
// @match        https://*.bing.com/*
// @license      GNU GPLv3
// @icon         https://www.bing.com/favicon.ico
// @connect      gumengya.com
// @run-at       document-end
// @note         更新于 2024年9月10日
// @supportURL   https://greasyfork.org/zh-CN/users/1192640
// @homepageURL  https://greasyfork.org/zh-CN/users/1192640
// @grant        GM_registerMenuCommand
// @grant        GM_addStyle
// @grant        GM_openInTab
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @namespace    https://greasyfork.org/zh-CN/users/1192640
// ==/UserScript==

var max_rewards = 30; //重复执行的次数
//每执行4次搜索后插入暂停时间,解决账号被监控不增加积分的问题
var pause_time = 6; // 暂停时长建议为10分钟（600000毫秒=10分钟）
var search_words = []; //搜索词
var default_search_words = ["盛年不重来，一日难再晨", "千里之行，始于足下", "少年易学老难成，一寸光阴不可轻", "敏而好学，不耻下问", "海内存知已，天涯若比邻", "三人行，必有我师焉",
    "莫愁前路无知已，天下谁人不识君", "人生贵相知，何用金与钱", "天生我材必有用", "海纳百川有容乃大；壁立千仞无欲则刚", "穷则独善其身，达则兼济天下", "读书破万卷，下笔如有神",
    "学而不思则罔，思而不学则殆", "一年之计在于春，一日之计在于晨", "莫等闲，白了少年头，空悲切", "少壮不努力，老大徒伤悲", "一寸光阴一寸金，寸金难买寸光阴", "近朱者赤，近墨者黑",
    "吾生也有涯，而知也无涯", "纸上得来终觉浅，绝知此事要躬行", "学无止境", "己所不欲，勿施于人", "天将降大任于斯人也", "鞠躬尽瘁，死而后已", "书到用时方恨少", "天下兴亡，匹夫有责",
    "人无远虑，必有近忧", "为中华之崛起而读书", "一日无书，百事荒废", "岂能尽如人意，但求无愧我心", "人生自古谁无死，留取丹心照汗青", "吾生也有涯，而知也无涯", "生于忧患，死于安乐"]
//{weibohot}微博热搜榜/{bilihot}哔哩热搜榜/{douyinhot}抖音热搜榜/{zhihuhot}知乎热搜榜/{baiduhot}百度热搜榜

var keywords_source = ['ZhiHuHot','WeiBoHot','TouTiaoHot','DouYinHot', 'BaiduHot'];
var random_keywords_source = keywords_source[Math.floor(Math.random() * keywords_source.length)]
//每次运行时随机获取一个热门搜索词来源用来作为关键词
function douyinhot_dic() {
    return new Promise((resolve, reject) => {
        // 发送GET请求到指定URL
        fetch("https://api.gumengya.com/Api/" + random_keywords_source)
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
    location.href = "https://www.bing.com/?br_msg=Please-Wait"; // 跳转到Bing首页
}, 'o');

// 定义菜单命令：停止
let menu2 = GM_registerMenuCommand('停止', function () {
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
    let randomDelay = Math.floor(Math.random() * 20000) + 10000; // 10000 毫秒 = 10 秒
    let randomString = generateRandomString(4); //生成4个长度的随机字符串
    let randomCvid = generateRandomString(32); //生成32位长度的cvid
    'use strict';

    // 检查计数器的值，若为空则设置为超过最大搜索次数
    if (GM_getValue('Cnt') == null) {
        GM_setValue('Cnt', max_rewards + 10);
    }

    // 获取当前搜索次数
    let currentSearchCount = GM_getValue('Cnt');

    // 根据计数器的值选择搜索引擎
    if (currentSearchCount <= max_rewards / 2) {
        let tt = document.getElementsByTagName("title")[0];
        tt.innerHTML = "[" + currentSearchCount + " / " + max_rewards + "] " + tt.innerHTML; // 在标题中显示当前搜索次数

        setTimeout(function () {
            GM_setValue('Cnt', currentSearchCount + 1); // 将计数器加1
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

        setTimeout(function () {
            GM_setValue('Cnt', currentSearchCount + 1); // 将计数器加1
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
}
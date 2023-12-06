// ==UserScript==
// @name         Microsoft Bing Rewards每日任务脚本
// @version      V1.0.9
// @description  自动完成微软Rewards每日搜索任务,每次运行时获取抖音/微博/哔哩哔哩/百度热门词,避免使用同样的搜索词被封号。
// @note         更新于 2023年12月06日
// @author       怀沙2049
// @match        https://www.bing.com/*
// @match        https://cn.bing.com/*
// @license      GNU GPLv3
// @icon         https://www.bing.com/favicon.ico
// @connect      tenapi.cn
// @run-at       document-end
// @grant        GM_registerMenuCommand
// @grant        GM_addStyle
// @grant        GM_openInTab
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @namespace    https://greasyfork.org/zh-CN/scripts/477107
// ==/UserScript==

var max_rewards = 50; /*重复执行的次数*/
var search_words=[]; //搜索词
//{weibohot}微博热搜榜/{bilihot}哔哩热搜榜/{douyinhot}抖音热搜榜/{zhihuhot}知乎热搜榜/{baiduhot}百度热搜榜
var keywords_source = "weibohot";

//获取抖音热门搜索词用来作为关键词
function douyinhot_dic() {
    return new Promise((resolve, reject) => {
        // 发送GET请求到指定URL
        fetch("https://tenapi.cn/v2/"+ keywords_source)
            .then(response => response.json()) // 将返回的响应转换为JSON格式
            .then(data => {
                // 提取每个元素的name属性值
                const names = data.data.map(item => item.name);
                resolve(names); // 将name属性值作为Promise对象的结果返回
            })
            .catch(error => {
                reject(error); // 将错误信息作为Promise对象的错误返回
            });
    });
}
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

// 自动将字符串中的字符进行替换
function AutoStrTrans(st) {
    let yStr = st; // 原字符串
    let rStr = ""; // 插入的混淆字符，可以自定义自己的混淆字符串
    let zStr = ""; // 结果字符串
    let prePo = 0;
    for (let i = 0; i < yStr.length;) {
        let step = parseInt(Math.random() * 5) + 1; // 随机生成步长
        if (i > 0) {
            zStr = zStr + yStr.substr(prePo, i - prePo) + rStr; // 将插入字符插入到相应位置
            prePo = i;
        }
        i = i + step;
    }
    if (prePo < yStr.length) {
        zStr = zStr + yStr.substr(prePo, yStr.length - prePo); // 将剩余部分添加到结果字符串中
    }
    return zStr;
}

// 生成指定长度的包含大写字母、小写字母和数字的随机字符串
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

    // 根据计数器的值选择搜索引擎
    if (GM_getValue('Cnt') <= max_rewards / 2) {
        let tt = document.getElementsByTagName("title")[0];
        tt.innerHTML = "[" + GM_getValue('Cnt') + " / " + max_rewards + "] " + tt.innerHTML; // 在标题中显示当前搜索次数

        setTimeout(function () {
            GM_setValue('Cnt', GM_getValue('Cnt') + 1); // 将计数器加1
            let nowtxt = search_words[GM_getValue('Cnt')]; // 获取当前搜索词
            nowtxt = AutoStrTrans(nowtxt); // 对搜索词进行替换
            location.href = "https://www.bing.com/search?q=" + encodeURI(nowtxt) + "&form=" + randomString + "&cvid=" + randomCvid; // 在Bing搜索引擎中搜索
        }, randomDelay);
    }

    if (GM_getValue('Cnt') > max_rewards / 2 && GM_getValue('Cnt') < max_rewards) {
        let tt = document.getElementsByTagName("title")[0];
        tt.innerHTML = "[" + GM_getValue('Cnt') + " / " + max_rewards + "] " + tt.innerHTML; // 在标题中显示当前搜索次数

        setTimeout(function () {
            GM_setValue('Cnt', GM_getValue('Cnt') + 1); // 将计数器加1
            let nowtxt = search_words[GM_getValue('Cnt')]; // 获取当前搜索词
            nowtxt = AutoStrTrans(nowtxt); // 对搜索词进行替换
            location.href = "https://cn.bing.com/search?q=" + encodeURI(nowtxt) + "&form=" + randomString + "&cvid=" + randomCvid; // 在Bing搜索引擎中搜索
        }, randomDelay);
    }
};
// ==UserScript==
// @name         移动端微软Rewards每日任务脚本
// @version      2023.11.20
// @description  自动完成移动端微软Rewards每日搜索任务,每次运行时获取抖音热门词,并增加随机延迟时间来避免被检测。
// @author       怀沙2049
// @match        https://www.bing.com/*
// @match        https://cn.bing.com/*
// @license      GNU GPLv3
// @icon         https://www.bing.com/favicon.ico
// @connect      tenapi.cn
// @run-at       document-end
// @note         更新于 2023年11月20日13:10
// @supportURL   https://greasyfork.org/zh-CN/users/1192640-huaisha1224
// @homepageURL  https://greasyfork.org/zh-CN/users/1192640-huaisha1224
// @grant        GM_registerMenuCommand
// @grant        GM_addStyle
// @grant        GM_openInTab
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @namespace    https://greasyfork.org/zh-CN/users/1192640-huaisha1224
// ==/UserScript==

var max_rewards = 25; //重复执行的次数
var search_words = []; //搜索词

//获取抖音热门搜索词用来作为关键词
function douyinhot_dic() {
    return new Promise((resolve, reject) => {
        // 发送GET请求到指定URL
        fetch("https://tenapi.cn/v2/douyinhot")
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


function exec() {
    // 生成随机延迟时间
    let randomDelay = Math.floor(Math.random() * 7000) + 1000; // 1000 毫秒 = 1 秒, 7000 毫秒 = 7 秒
    let randomString = Math.random().toString(36).substr(2, 4).toUpperCase(); //生成4个长度的随机字符串
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
            location.href = "https://www.bing.com/search?q=" + encodeURI(nowtxt) + "&form=" + randomString; // 在Bing搜索引擎中搜索
        }, randomDelay);
    }

    if (GM_getValue('Cnt') > max_rewards / 2 && GM_getValue('Cnt') < max_rewards) {
        let tt = document.getElementsByTagName("title")[0];
        tt.innerHTML = "[" + GM_getValue('Cnt') + " / " + max_rewards + "] " + tt.innerHTML; // 在标题中显示当前搜索次数

        setTimeout(function () {
            GM_setValue('Cnt', GM_getValue('Cnt') + 1); // 将计数器加1
            let nowtxt = search_words[GM_getValue('Cnt')]; // 获取当前搜索词
            location.href = "https://cn.bing.com/search?q=" + encodeURI(nowtxt) + "&form=" + randomString; // 在Bing搜索引擎中搜索
        }, randomDelay);
    }
};
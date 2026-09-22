// Usage: node scripts/browser_check.cjs [playwright module] [screenshot directory]
const {chromium} = require(process.argv[2] || 'playwright');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../public');
const screenshots = process.argv[3];
const types = {'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.json':'application/json','.png':'image/png'};
const server = http.createServer((req,res) => {
  let name = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  if (!name.startsWith('/YangMame/')) {res.writeHead(404);res.end();return;}
  name = name.slice('/YangMame/'.length); if (!name || name.endsWith('/')) name += 'index.html';
  const file = path.resolve(root,name);
  if (!file.startsWith(root+path.sep) || !fs.existsSync(file)) {res.writeHead(404);res.end();return;}
  res.setHeader('Content-Type',types[path.extname(file)] || 'application/octet-stream');res.end(fs.readFileSync(file));
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base = `http://127.0.0.1:${server.address().port}/YangMame/`;
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage();const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    for (const viewport of [{width:1440,height:1000},{width:390,height:844}]) {
      await page.setViewportSize(viewport);await page.goto(base);
      assert.equal(await page.locator('.post-card').count(),5);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Home overflows');
      if(screenshots){fs.mkdirSync(screenshots,{recursive:true});await page.screenshot({path:path.join(screenshots,`home-${viewport.width}.png`),fullPage:true});}
      await page.goto(base+'lg-gram.html');
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Article overflows');
      assert(await page.locator('pre code').count()>0);
      await page.goto(base+'search/?q=EAPI');
      await page.waitForFunction(()=>document.querySelector('#search-status').textContent.startsWith('找到'));
      assert(await page.locator('#results a').count()>0);
      await page.locator('#query').fill('不存在的关键词987654321');await page.locator('button').click();
      await page.waitForFunction(()=>document.querySelector('#search-status').textContent.startsWith('没有找到'));
      await page.goto(base+encodeURIComponent('mpd-ncmpcpp配置美化教程')+'.html');
      await page.waitForFunction(()=>[...document.images].every(img=>img.complete&&img.naturalWidth>0));
    }
    assert.deepEqual(errors,[]);console.log('Desktop/mobile layout, images, code, search and no-results checks passed.');
  } finally {await browser.close();server.close();}
})().catch(error=>{console.error(error);server.close();process.exitCode=1;});

(function () {
  "use strict";

  var COPY_ZH = {
    nav_evidence: "实证数据",
    nav_proof: "10 秒自检",
    nav_workflow: "开发流嵌入",
    nav_skills: "6 个 Skills",
    nav_arch: "三层防线",
    pill_zero: "零框架绑定",
    pill_polyglot: "Python · TS/JS · Go · Rust · Java",
    hero_title: "别让 Coding Agent 既当选手又当裁判。",
    hero_sub: "给“代码由 Coding Agent 来写”的仓库准备的一套护栏：Agent 会读的规则、它跳不过的确定性本地检查，以及它无法自己批准自己的 GitHub 合并边界。",
    hero_meta: "提炼自 2000+ 亿 Token 真实多仓 AI 辅助工程实践，配套分母明确的专项研究、14 用例多语言评测与 Fail-Closed 脚本。",
    cta_audit: "10 秒体检你的仓库",
    cta_skills: "安装 6 个独立 Skills",
    cta_evidence: "阅读完整实证数据 ↗",
    ev_eyebrow: "一线实证数据 · 严格区分分母",
    ev_title: "为什么绿灯单测依然会放行坏掉的 AI 代码",
    ev_desc: "本仓库每一条规则都源自真实生产事故，而不是泛泛的 Prompt 技巧。每项量化结论均严格绑定对应样本分母。",
    stat1_label: "累计多仓 AI 工程实战体量（Token）",
    stat1_note: "Claude Code、Cursor 与 Codex 并发协作，覆盖 Python、TS/React 与 Rust",
    stat2_label: "CI 与单测合计捕获的前端 Bug 比例",
    stat2_note: "454 个去重前端缺陷（~10 万行）；前 4 类根因占 84%",
    stat3_label: "CI 捕获的后端性能事故比例",
    stat3_note: "100+ 项真实修复（~38 万行）；仅 16% 在压垮前主动发现",
    stat4_label: "AI Code Review 经取证复核后留下的真阻断项",
    stat4_note: "另有 15/15 → 0/15 旧门禁漂移与 0/33 架构图无条件准确",
    chart1_title: "454 个前端缺陷：前 4 类根因占 84%",
    chart1_sub: "基于 321 个明确归因的 React/TypeScript 缺陷样本",
    chart2_title: "上下文悬崖与规模相变临界点",
    chart2_sub: "基于 443 次追踪会话 / 84 亿 Token 专项样本集",
    proof_eyebrow: "10 秒实证体检 · 零 pip install",
    proof_title: "直接对着你自己的仓库跑一遍",
    proof_desc: "不必轻信文档宣传。用纯 Python 标准库对任意本地仓库跑一次只读体检，或在 CI 中直接贴入 4 行可复用 GitHub Action。",
    tab_audit: "10 秒自检脚本",
    tab_skills: "安装 6 个 Skills",
    tab_action: "4 行 CI Action",
    tab_bootstrap: "一键落地 L0–L2",
    copy: "复制",
    wf_eyebrow: "AI 编码真实的一天",
    wf_title: "不换工具，精准卡在 5 个高危交接点",
    wf_desc: "继续用 Claude Code、Cursor、Codex 和 superpowers 做编码内环；把 agentic-sdlc 像安全带与刹车一样套在最容易翻车的 5 个节点。",
    step1_t: "1. 接单开工",
    step1_d: "统一读根目录 AGENTS.md 与 STATUS.md，从 origin/main 开隔离 Worktree，并用 workspace-git.py 钩子物理拦截直提交 main。",
    step2_t: "2. 规划与写码",
    step2_d: "非平凡改动（>3 文件或 >50 行）先定边界与失败测试；写到鉴权、租户、危险 Sink、密钥或依赖时自动触发 secure-vibe-coding。",
    step3_t: "3. 喊“完成”之前",
    step3_d: "运行 done-claim-verify 与 audit-pr-diff：核验 4 个假完成断点，输出带精确命令、退出码与 does_not_prove[] 的 DoneClaim。",
    step4_t: "4. 开 PR 与 CI",
    step4_d: "运行 40 位 SHA 锁定的多语言 Fail-Closed CI 与 4 行 action.yml，拦截多语言危险 Sink 与 --passWithNoTests；评审直接引用 OAS-* 编号。",
    step5_t: "5. 合并与上线",
    step5_d: "导入不可自证 GitHub Ruleset 与 CODEOWNERS；发版前运行五维 audit-production-readiness，输出 H1 生产级 vs H2 Demo 级裁决。",
    sk_eyebrow: "6 个独立自包含 Skills · 脱离具体编程语言",
    sk_title: "零重叠护栏，按需加载零常态开销",
    sk_desc: "这 6 个 Skills 沉淀的是跨语言安全红线、验收核查、审计与 Git 不变量（不包含代码风格规范），每个 Skill 均显式声明自身非权威。",
    sk1: "检查目标仓库真实技术栈，安全落地统一 AGENTS.md、极薄 @AGENTS.md CLAUDE.md、STATUS.md、PR 模板与 Fail-Closed CI，绝不覆盖已有文件。",
    sk2: "强制默认拒绝鉴权/租户隔离、参数化查询、安全 Sink、SSRF 169.254.169.254 防护、零兜底密钥、防幻觉包投毒与反向安全单测。",
    sk3: "基于 file:line 取证审查分支 diff，覆盖七宗罪、安全红线、前端 454 Bug、后端 8 类性能陷阱与门禁面变更审查。",
    sk4: "整仓五维实现审计（架构/设计/功能/性能/安全），落实 7 条证据纪律、三层默认值核查、数据活性与 H1/H2 生产 vs Demo 裁决。",
    sk5: "拒绝裸布尔 done=true；保留 NOT_RUN/FAIL/ERROR/CONFLICT，解引用 4 个假完成断点，强制输出 DoneClaim 与 does_not_prove[]。",
    sk6: "通过远端基线刷新、Worktree 隔离、Managed Issue Claim、跨会话契约交接、禁 Stacked PR 与 5 项安全清理协调多 Agent 并发。",
    ar_eyebrow: "零信任与不可自证（Non-Self-Attestation）",
    ar_title: "三层纵深防线",
    ar_desc: "Prompt 里的文字规则会随上下文压缩不断衰减，真正的信任边界必须建在模型窗口之外。",
    l1_t: "第一层 · Agent 内环（易用性，非权威）",
    l1_d: "6 个独立 Skills · llms.txt（约 1K-token 路由表）· 统一根目录 AGENTS.md + 极薄 @AGENTS.md CLAUDE.md · 8 套实证清单。",
    l2_t: "第二层 · 本地确定性护栏",
    l2_d: "零依赖多语言 audit-repo.py（Python/JS/TS/Go/Rust/Java）· 可卸载 Git 钩子（workspace-git.py）· 按 lockfile 寻址共享 Node 仓 · 即将开源的 Rust 本地工程承载 deps 与 sealed-data。",
    l3_t: "第三层 · GitHub 外部合并边界（不可自证）",
    l3_d: "40 位 SHA 锁定多语言 CI 模板 · 4 行可复用 action.yml · 门禁面 CODEOWNERS · 可导入 Branch Ruleset JSON · 只读 observe-github-ruleset.py。",
    lim_title: "诚实边界（does_not_prove）",
    lim1: "Markdown 规则与 Skills 只是易用性投影，无法防住蓄意 Prompt 注入，也不能在支付、鉴权或生产运维上替代人类工程判断。",
    lim2: "PR 受控源码运行的 CI 与本地自检始终属于 candidate / advisory，绝不构成可自证的合并权威。",
    lim3: "静态检查只捕获高信噪比结构与供应链缺陷；运行期业务逻辑与 P99 负载仍需真实集成测试与外部门禁保障。",
    footer_sub: "Apache-2.0 · 零运行依赖 · 为在真实生产代码库中使用 Coding Agent 的工程师打造。"
  };

  var COPY_EN = {};
  var nodes = document.querySelectorAll("[data-i18n]");
  for (var i = 0; i < nodes.length; i++) {
    var key = nodes[i].getAttribute("data-i18n");
    if (key) {
      COPY_EN[key] = nodes[i].textContent;
    }
  }

  function applyLang(lang) {
    var dict = lang === "zh" ? COPY_ZH : COPY_EN;
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    for (var j = 0; j < nodes.length; j++) {
      var k = nodes[j].getAttribute("data-i18n");
      if (k && Object.prototype.hasOwnProperty.call(dict, k)) {
        nodes[j].textContent = dict[k];
      }
    }
    var langBtn = document.getElementById("lang-toggle");
    if (langBtn) {
      langBtn.textContent = lang === "zh" ? "EN" : "中文";
    }
    try {
      window.localStorage.setItem("oas-lang", lang);
    } catch (_err) {
      // Storage may be disabled in privacy modes; ignore safely.
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    var themeBtn = document.getElementById("theme-toggle");
    if (themeBtn) {
      themeBtn.textContent = theme === "light" ? "☾" : "☀";
    }
    try {
      window.localStorage.setItem("oas-theme", theme);
    } catch (_err) {
      // Ignore storage failures cleanly.
    }
  }

  var initialLang = "en";
  var initialTheme = "dark";
  try {
    var savedLang = window.localStorage.getItem("oas-lang");
    if (savedLang === "zh" || savedLang === "en") {
      initialLang = savedLang;
    }
    var savedTheme = window.localStorage.getItem("oas-theme");
    if (savedTheme === "light" || savedTheme === "dark") {
      initialTheme = savedTheme;
    }
  } catch (_err) {
    // Fall back to defaults.
  }

  applyTheme(initialTheme);
  if (initialLang === "zh") {
    applyLang("zh");
  }

  var langToggle = document.getElementById("lang-toggle");
  if (langToggle) {
    langToggle.addEventListener("click", function () {
      var current = document.documentElement.lang.indexOf("zh") === 0 ? "zh" : "en";
      applyLang(current === "zh" ? "en" : "zh");
    });
  }

  var themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme") || "dark";
      applyTheme(current === "light" ? "dark" : "light");
    });
  }

  var tabs = document.querySelectorAll(".tab");
  var panels = document.querySelectorAll(".tab-panel");
  for (var t = 0; t < tabs.length; t++) {
    tabs[t].addEventListener("click", function () {
      var targetId = this.getAttribute("data-tab");
      for (var k = 0; k < tabs.length; k++) {
        var active = tabs[k] === this;
        tabs[k].classList.toggle("active", active);
        tabs[k].setAttribute("aria-selected", active ? "true" : "false");
      }
      for (var p = 0; p < panels.length; p++) {
        panels[p].classList.toggle("active", panels[p].id === targetId);
      }
    });
  }

  var copyButtons = document.querySelectorAll(".copy-btn");
  for (var c = 0; c < copyButtons.length; c++) {
    copyButtons[c].addEventListener("click", function () {
      var btn = this;
      var codeId = btn.getAttribute("data-copy");
      var codeEl = codeId ? document.getElementById(codeId) : null;
      if (!codeEl || !navigator.clipboard) {
        return;
      }
      var original = btn.textContent;
      navigator.clipboard.writeText(codeEl.textContent || "").then(function () {
        btn.textContent = document.documentElement.lang.indexOf("zh") === 0 ? "已复制" : "Copied";
        window.setTimeout(function () {
          btn.textContent = original;
        }, 1400);
      });
    });
  }
})();

(function () {
  "use strict";

  var COPY_ZH = {
    nav_evidence: "实证数据",
    nav_ontology: "本体论",
    nav_quickstart: "10 秒验证",
    nav_workflow: "开发流",
    nav_skills: "6 个 Skills",
    meta_zero: "零框架依赖",
    meta_langs: "Python · TS/JS · Go · Rust · Java",
    hero_title: "别让 Coding Agent 既当选手又当裁判。",
    hero_lead: "为 AI 参与写代码的仓库准备的纯文件护栏：Agent 会读的规则、它跳不过的确定性本地检查，以及它无法自己批准自己的 GitHub 合并边界。",
    hero_note: "提炼自 2000+ 亿 Token 多仓工程实践与 15,384 条真实 Claude Code / Codex 对话——由 9 大实体、5 条公理、9 篇标准、6 个独立 Skills 与零依赖验证脚本统一收口。",
    cta_audit: "10 秒体检你的仓库",
    cta_ontology: "阅读本体论总纲 ↗",
    cta_release: "v0.4.0 正式版 ↗",
    ev_kicker: "01 · 一线实证数据",
    ev_title: "为什么绿灯单测依然会放行坏掉的 AI 代码",
    ev_desc: "每一条控制规则都源自真实生产事故，且严格绑定各自独立分母，绝不跨样本夸大。",
    m1_l: "多仓生产实战累计 Token",
    m1_s: "另分析 15,384 条真实 Claude Code / Codex 工程对话",
    m2_l: "CI 与单测捕获的前端 Bug",
    m2_s: "454 个去重缺陷（~10 万行）；前 4 类根因占 84%",
    m3_l: "CI 捕获的后端性能修复",
    m3_s: "100+ 项真实修复（~38 万行）；仅 16% 为主动发现",
    m4_l: "AI Review 经复核留下的真阻断",
    m4_s: "另有 15/15 → 0/15 旧门禁漂移与 0/33 架构图准确",
    c1_title: "454 个前端缺陷 · 前 4 类根因占 84%",
    c1_sub: "基于 321 个明确归因的 React/TypeScript 缺陷样本",
    c2_title: "规模相变临界点与上下文悬崖",
    c2_sub: "基于 443 次追踪会话 / 84 亿 Token 专项样本集",
    on_kicker: "02 · AGENTIC SDLC 本体论（v0.2.0 新增）",
    on_title: "五条公理，从根源消除 Agent 本体混淆",
    on_desc: "Agent 反复翻车很少是因为漏看清单文字，而是把会话记忆混成代码现实、把单文件修改混成耦合完成、把总结混成证据。",
    a1_t: "公理 1 · 事实压倒记忆（Reality > Memory）",
    a1_d: "新鲜拉取的 origin/main、真实调用链与构造点、STATUS.md 以及只读运行态探针无条件压倒会话记忆与过时文档。",
    a2_t: "公理 2 · 耦合变更闭包（ArtifactGraph）",
    a2_d: "修改源码、API 或 Schema 后，在耦合的单测、契约、文档与 STATUS.md 全部同步前，状态只能是 PARTIAL——由 scripts/check-change-sync.py 强制守门。",
    a3_t: "公理 3 · 状态不可有损折叠",
    a3_d: "NOT_RUN、UNKNOWN、RESULT_UNKNOWN、CONFLICT 与 ERROR 是一等互斥状态；严禁压缩成布尔 true 或假默认值（?? 0 / || []）。",
    a4_t: "公理 4 · 主体与裁判分离（Non-Self-Attestation）",
    a4_d: "产出 Patch 的执行主体永不具备认证自身 Gate 变更的权威；受保护 GitHub Ruleset 与独立机制审查掌握最终合并边界。",
    a5_t: "公理 5 · 不对称知识演化",
    a5_d: "生产事故必须升级为负向变异测试与确定性门禁；自动学习只能收紧约束或补上下文，绝不能自动放宽权限或取消审批。",
    qs_kicker: "03 · 10 秒零安装验证",
    qs_title: "直接对着你自己的仓库跑一遍",
    qs_desc: "纯 Python 3.11+ 标准库、严格只读、零 pip install。跑一条命令，立刻看到自己代码库里的真实盲区。",
    t_audit: "10 秒自检",
    t_sync: "耦合同步门禁",
    t_skills: "6 个 Skills",
    t_action: "4 行 CI Action",
    t_boot: "一键落地 L0–L2",
    copy: "复制",
    sample_lbl: "典型仓库的真实拦截输出示例",
    wf_kicker: "04 · 工作流嵌入",
    wf_title: "不换现有工具，卡住 5 个高危交接点",
    wf_desc: "继续用 Claude Code、Cursor、Codex 与 superpowers 写代码，只把确定性护栏套在最容易翻车的 5 个节点上。",
    w1_t: "接单开工",
    w1_d: "统一读根目录 AGENTS.md 与 STATUS.md，开隔离 Worktree，并用 workspace-git.py 物理拦住直提交 main。",
    w2_t: "规划与写码",
    w2_d: "执行非平凡任务阈值（>3 文件 / >50 行）、secure-vibe-coding 及写码前可靠性与性能不变量。",
    w3_t: "喊“完成”前",
    w3_d: "跑 check-change-sync.py、done-claim-verify 与 audit-pr-diff，输出带 does_not_prove[] 的 DoneClaim。",
    w4_t: "开 PR 与 CI",
    w4_d: "运行 40 位 SHA 锁定的多语言 Fail-Closed CI 与 4 行 action.yml，评审直接引用 OAS-* 规则编号。",
    w5_t: "合并与上线",
    w5_d: "启用不可自证 GitHub Ruleset 与 CODEOWNERS；发版前运行五维 audit-production-readiness（H1/H2 裁决）。",
    sk_kicker: "05 · 6 个独立 Skills 与 9 篇标准",
    sk_title: "脱离具体编程语言，按需加载零常态负担",
    sk_desc: "Skills 沉淀的是跨语言安全、可靠、审计与 Git 不变量（不包含格式/代码风格规则），且全部显式声明自身非权威。",
    s1: "探测目标仓库真实技术栈，安全落地统一 AGENTS.md、极薄 @AGENTS.md CLAUDE.md、STATUS.md、PR 模板与 Fail-Closed CI。",
    s2: "强制默认拒绝鉴权/租户隔离、安全 Sink、SSRF 169.254.169.254 防护、默认 mutating 工具白名单、防只读外泄与反向安全单测。",
    s3: "基于 file:line 取证审查 diff，覆盖七宗罪、安全红线、前端 454 Bug、后端 8 类性能陷阱与门禁面变更审查。",
    s4: "整仓五维审计，落实 7 条证据纪律、三层默认值、数据活性、发版前运维红线、自学习不对称与 H1/H2 裁决。",
    s5: "拒绝裸布尔 done=true；保留非绿状态、解引用 4 个假完成断点、校验耦合同步并强制声明 does_not_prove[]。",
    s6: "以远端基线刷新、隔离 Worktree、Managed Issue Claim、跨会话契约交接、禁 Stacked PR 与安全清理协调多 Agent 并发。",
    lim_h: "诚实边界（does_not_prove）",
    lim_p: "Markdown 规则与 Skills 只是易用性投影，绝不构成合并权威。PR 受控 CI 与本地自检始终属于 candidate / advisory；支付、鉴权、运行期语义与 P99 负载仍需真实集成测试、受保护 GitHub Ruleset 与人类工程判断。"
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
    var btn = document.getElementById("lang-toggle");
    if (btn) {
      btn.textContent = lang === "zh" ? "EN" : "中文";
    }
    try {
      window.localStorage.setItem("oas-lang", lang);
    } catch (_err) {
      // Ignore storage errors cleanly.
    }
  }

  try {
    var saved = window.localStorage.getItem("oas-lang");
    if (saved === "zh") {
      applyLang("zh");
    }
  } catch (_err) {
    // Default to English.
  }

  var langToggle = document.getElementById("lang-toggle");
  if (langToggle) {
    langToggle.addEventListener("click", function () {
      var isZh = document.documentElement.lang.indexOf("zh") === 0;
      applyLang(isZh ? "en" : "zh");
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

# SEOULMALL Coupang Curation: Standardized Responsive Post-Footer Card Specification
**Target Networks**: 25 WordPress Sites (WP25) & 33 Blogspot Blogs (Blogger33)  
**Author**: WP & Blogspot Publishing Leader (`@wp-leader`)  
**Canonical Store Hub**: `https://influencers.coupang.com/s/seoulshop` (SEOULMALL)  
**Status**: **DEPLOYED & ACTIVE** (`automation_hub/seoulmall_widget.py`)  

---

## 1. Architectural Overview & Policy Alignment

Under the swarm directive from `@coordinator` (Message #36) and in strict coordination with `@adsense-gatekeeper`, `@cpc-scout`, and `@health-writer`, the SEOULMALL Coupang curation module has been standardized across all 25 WordPress properties and 33 Blogspot blogs.

### Key Technical Standards:
1. **Canonical Influencer URL**: `https://influencers.coupang.com/s/seoulshop`
   - Configurable sub-tracking (`subId`) per channel/vertical (e.g., `?subId=wp_khealth365_joint`, `?subId=blogger_oliveyoung`).
2. **Search Engine & Legal Attributes**:
   - `rel="nofollow sponsored noopener"` enforced on every outward product and store link.
   - `target="_blank"` with isolated opener protection.
3. **Dual FTC Statutory Disclosures**:
   - **Korean**: `※ 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.`
   - **English**: `※ This article contains Coupang Partners affiliate links. We may earn a commission at no extra cost to you.`
4. **AdSense Safety Gating Framework**:
   - **Approved Sites (`k-health365.com` & Blogger33)**: Full responsive card and contextual in-text linking active.
   - **24 Pending WordPress Sites (Review Period)**: Strict throttle/freeze enforced (0% affiliate cards on foundational pillar content) to eliminate Google AdSense "Thin Affiliate" and "Low Value Content" rejection risks.

---

## 2. Standardized Card Component Matrix

The standardized component supports three purpose-built vertical variants matching our editorial pillars:

| Vertical Variant | Target Domains / Categories | Visual Accent | Badge Text | Featured Category Chips |
| :--- | :--- | :--- | :--- | :--- |
| **K-Health** | `k-health365.com`, `job.k-health365.com`, Blogger Health | Emerald Green (`#059669`) | K-Health Official Curation | 관절·연골, 혈당·대사, 수면·마그네슘, 항산화·면역, 간 건강·피로 |
| **K-Beauty** | `kskin365.com`, `oliveyoungkorea.com`, Blogger Beauty | Fuchsia Pink (`#db2777`) | K-Beauty Curated Store | 피부장벽 리페어, 시카·어성초 진정, PDRN·콜라겐, 데일리 선케어, 마스크팩 |
| **General Living** | `korea365.org`, `k-trip365.com`, Blogger Life/Expat | Royal Violet (`#7c3aed`) | Coupang Influencer Official Store | K-Health, K-Beauty, Korea Travel, Sim & eSIM, Living & Food |

---

## 3. Responsive HTML & CSS Production Code

```html
<!-- seoulmall-store-widget:v2 -->
<section class="seoulmall-card-container" aria-label="SeoulMall Curated Store">
  <style>
    .seoulmall-card-container {
      box-sizing: border-box;
      max-width: 880px;
      margin: 36px auto 20px auto;
      padding: clamp(18px, 4vw, 28px);
      border: 1px solid #bbf7d0;
      border-radius: 16px;
      background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 50%, #ecfdf5 100%);
      text-align: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
    }
    .seoulmall-card-container * { box-sizing: border-box; }
    .seoulmall-badge {
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #059669;
      background: #ffffff;
      padding: 4px 12px;
      border-radius: 999px;
      border: 1px solid #bbf7d0;
      margin-bottom: 10px;
    }
    .seoulmall-title {
      margin: 6px 0 8px 0;
      color: #1e293b;
      font-size: clamp(22px, 4vw, 30px);
      font-weight: 800;
      line-height: 1.25;
    }
    .seoulmall-tagline {
      margin: 0 auto 16px auto;
      color: #475569;
      font-size: clamp(13px, 2.5vw, 15px);
      line-height: 1.5;
      max-width: 600px;
    }
    .seoulmall-chips {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 6px;
      margin: 14px 0 20px 0;
    }
    .seoulmall-chips span {
      padding: 6px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 999px;
      background: #ffffff;
      color: #334155;
      font-size: 12px;
      font-weight: 600;
    }
    .seoulmall-cta-btn {
      display: inline-block;
      max-width: 100%;
      padding: 13px 28px;
      border-radius: 999px;
      background: linear-gradient(90deg, #059669, #10b981);
      color: #ffffff !important;
      text-decoration: none !important;
      font-weight: 700;
      font-size: 15px;
      letter-spacing: -0.01em;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .seoulmall-cta-btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.16);
    }
    .seoulmall-ftc {
      margin: 16px 0 0 0;
      color: #64748b;
      font-size: 11px;
      line-height: 1.5;
      border-top: 1px dashed #cbd5e1;
      padding-top: 12px;
    }
    .seoulmall-ftc p { margin: 2px 0; }
    @media (max-width: 600px) {
      .seoulmall-card-container { margin: 24px 0; padding: 18px 12px; }
      .seoulmall-cta-btn { width: 100%; padding: 13px 16px; font-size: 14px; }
      .seoulmall-chips span { font-size: 11px; padding: 5px 9px; }
    }
  </style>
  <div class="seoulmall-badge">K-Health Official Curation</div>
  <h3 class="seoulmall-title">SEOULMALL 헬스 & 영양제 케어</h3>
  <p class="seoulmall-tagline">식약처 인증 관절 영양제, 고순도 MSM, 콘드로이친 특가 모음</p>
  <div class="seoulmall-chips">
    <span>관절·연골</span><span>혈당·대사</span><span>수면·마그네슘</span><span>항산화·면역</span><span>간 건강·피로</span>
  </div>
  <a class="seoulmall-cta-btn" href="https://influencers.coupang.com/s/seoulshop?subId=khealth365_footer" target="_blank" rel="nofollow sponsored noopener">SEOULMALL 추천 상품 보러가기 →</a>
  <div class="seoulmall-ftc">
    <p>※ 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
    <p>※ This article contains Coupang Partners affiliate links. We may earn a commission at no extra cost to you.</p>
  </div>
</section>
```

---

## 4. Integration & Safe Dispatch Workflow

1. **WordPress Dispatch Integration**:
   - `scripts/daily_publication_floor.py` calls `automation_hub.seoulmall_widget.append_card_safe(content, domain, vertical)`.
   - Gatekeeper check `should_render_for_domain(domain)` confirms whether domain is approved (`k-health365.com`) or pending review.
2. **Blogger 33 Integration**:
   - `scripts/publish_blogger_33_now.py` automatically injects the responsive card into the post footer with the site's unique tracking identifier.
3. **Validation & Monitoring**:
   - Weekly verification audited by `@quality-reporter` to ensure 0% broken URLs, 100% presence of FTC disclosures, and 0% unsolicited popups.

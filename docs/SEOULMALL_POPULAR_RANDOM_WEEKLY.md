# SeoulMall weekly popularity export

The weekly GitHub workflow uses `scripts/rotate_coupang_weekly.py` at 00:05 KST and rotates only after the current set expires.

To activate selection, provide `config/affiliate/next-weekly-10-verified.json` as an authenticated export from the user's **own SeoulMall** storefront, with this shape:

```json
{
  "source": "seoulmall_verified_popularity_export",
  "storefront_url": "https://influencers.coupang.com/s/seoulmall",
  "source_of_truth": true,
  "owner_approved": true,
  "items": [
    {
      "id": "unique-product-id",
      "title": "Verified product name",
      "category": "k_beauty_skincare",
      "popularity_rank": 1,
      "url": "https://link.coupang.com/a/REAL_TRACKING_CODE",
      "image_url": "https://image.coupangcdn.com/image/affiliate/banner/REAL_IMAGE.jpg",
      "enabled": true,
      "affiliate_confirmed": true
    }
  ]
}
```

Provide at least five eligible items in each category, preferably 20+ per category. The selection samples **5 beauty + 5 health** without replacement, weighted by `1 / popularity_rank ** 0.7`, seeded by date and prior set ID. The selected ten must be different affiliate links from the preceding week's ten; if no verified alternatives exist, the rotation fails safely. Do not fabricate rankings, storefront URLs, image links, or affiliate codes.

**Important:** The public storefront page does not guarantee access to actual sales rankings. A manually exported, account-authorized popularity ranking or an approved official API feed is necessary. A collection's visual order is not proof of sales rank. Do not claim a live ranking without that evidence.

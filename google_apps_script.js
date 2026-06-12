// Google Sheets Apps Script 코드
// 붙여넣을 위치: 구글시트 → 확장 프로그램 → Apps Script

function doPost(e) {
  var ss    = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("포스팅 현황") || ss.getActiveSheet();
  var data  = JSON.parse(e.postData.contents);

  // 헤더가 없으면 자동 추가
  if (sheet.getLastRow() === 0) {
    sheet.appendRow([
      "날짜/시간","사이트","카테고리","키워드","제목",
      "상태","SEO점수","글자수","URL","실패사유","봇종류"
    ]);
    sheet.getRange(1,1,1,11).setFontWeight("bold")
         .setBackground("#1a73e8").setFontColor("#ffffff");
    sheet.setFrozenRows(1);
  }

  var row = [
    data.date     || new Date().toLocaleString("ko-KR"),
    data.site     || "",
    data.cat      || data.section || "",
    data.keyword  || data.title   || "",
    data.title    || "",
    data.status   || "",
    data.seo      || "",
    data.chars    || "",
    data.url      || data.post_url || "",
    data.reason   || "",
    data.bot_type || "auto",
  ];

  sheet.appendRow(row);

  var lastRow = sheet.getLastRow();
  var range   = sheet.getRange(lastRow, 1, 1, 11);

  // 성공=초록, 실패=빨강, 진행중=노랑
  if (String(data.status).includes("OK") || String(data.status).includes("✅")) {
    range.setBackground("#e8f5e9");
  } else if (String(data.status).includes("FAIL") || String(data.status).includes("❌")) {
    range.setBackground("#ffebee");
  } else {
    range.setBackground("#fff9c4");
  }

  // URL 하이퍼링크
  if (data.url || data.post_url) {
    var url = data.url || data.post_url;
    sheet.getRange(lastRow, 9).setFormula(`=HYPERLINK("${url}","열기")`);
  }

  return ContentService
    .createTextOutput(JSON.stringify({result:"ok",row:lastRow}))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  return ContentService.createTextOutput("The Seoul Journal Bot - Sheets Webhook OK");
}

// 매일 자동 요약 이메일 (선택사항)
function sendDailySummary() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data  = sheet.getDataRange().getValues();
  var today = new Date().toLocaleDateString("ko-KR");

  var ok   = 0, fail = 0;
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][0]).includes(today)) {
      if (String(data[i][5]).includes("OK")) ok++;
      else fail++;
    }
  }

  MailApp.sendEmail({
    to: "huh0303@gmail.com",
    subject: `[포스팅봇] ${today} 결과: 성공 ${ok}개 / 실패 ${fail}개`,
    body: `오늘 포스팅 현황\n\n✅ 성공: ${ok}개\n❌ 실패: ${fail}개\n\n구글시트에서 확인하세요.`
  });
}

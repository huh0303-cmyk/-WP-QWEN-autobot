param([int]$MaxNewCaptures=10)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$rootDir=Split-Path -Parent $PSScriptRoot
$planPath=Join-Path $rootDir 'data\affiliate\koreawedding365-8-category-capture-plan.json'
$outPath=Join-Path $rootDir 'reports\koreawedding365-8-category-captures-2026-11-01.ndjson'
$plan=Get-Content $planPath -Raw -Encoding UTF8 | ConvertFrom-Json
$chrome=Get-Process chrome | Where-Object {$_.MainWindowHandle -ne 0} | Select-Object -First 1
if(-not $chrome){throw 'Chrome window not found.'}
$doneIds=@()
if(Test-Path $outPath){foreach($line in Get-Content $outPath -Encoding UTF8){try{$rec=$line|ConvertFrom-Json;if($rec.status -eq 'CAPTURED' -and $rec.candidate_id){$doneIds+=([string]$rec.candidate_id)}}catch{}}}
function Get-Root { [System.Windows.Automation.AutomationElement]::FromHandle($chrome.MainWindowHandle) }
function Get-ByType($root,$type) {
 $c=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,$type)
 return ,($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$c))
}
function Get-Document($root) {
 $docs=Get-ByType $root ([System.Windows.Automation.ControlType]::Document)
 if($docs.Count -gt 0){return $docs.Item(0)}
 return $null
}
function Scroll-PageDown {
 $root=Get-Root;$doc=Get-Document $root
 if($doc){$doc.SetFocus()}
 [System.Windows.Forms.SendKeys]::SendWait('{PGDN}')
 Start-Sleep -Milliseconds 800
}
function Get-AddressEdit($root) {
 $edits=Get-ByType $root ([System.Windows.Automation.ControlType]::Edit)
 foreach($e in $edits){if($e.Current.Name -eq 'Address and search bar'){return $e}}
 return $null
}
function Get-LinkButton($root) {
 $buttons=Get-ByType $root ([System.Windows.Automation.ControlType]::Button)
 foreach($b in $buttons){$r=$b.Current.BoundingRectangle;if($b.Current.Name -eq '링크 생성' -and -not $b.Current.IsOffscreen -and $r.X -lt 250){return $b}}
 $candidates=@()
 foreach($b in $buttons){$r=$b.Current.BoundingRectangle;if(-not $b.Current.IsOffscreen -and $r.X -lt 220 -and $r.Y -gt 200 -and $r.Y -lt 500 -and $r.Width -gt 70 -and $r.Height -gt 25){$candidates+=,$b}}
 if($candidates.Count -eq 1){return $candidates[0]}
 if($candidates.Count -ge 2){$sorted=@($candidates|Sort-Object {$_.Current.BoundingRectangle.Y});return $sorted[1]}
 return $null
}
function Get-BlogTagRadio($root) {
 $radios=Get-ByType $root ([System.Windows.Automation.ControlType]::RadioButton)
 if($radios.Count -ge 2){return $radios.Item(1)}
 return $null
}
function Get-BlogTagText($root) {
 $texts=Get-ByType $root ([System.Windows.Automation.ControlType]::Text)
 foreach($t in $texts){$n=$t.Current.Name;if(($n -like '<iframe src=*' -and $n -like '*</iframe>*') -or ($n -like '<a href=*' -and $n -like '*</a>*')){return $n}}
 return $null
}
function Get-AddressUrl($root) {
 $doc=Get-Document $root
 if($doc){$doc.SetFocus()}
 [System.Windows.Forms.SendKeys]::SendWait('^l'); Start-Sleep -Milliseconds 150
 [System.Windows.Forms.SendKeys]::SendWait('^c'); Start-Sleep -Milliseconds 250
 return [System.Windows.Forms.Clipboard]::GetText()
}
function Get-Param([string]$url,[string]$key) {
 $enc=[uri]::EscapeDataString($key)
 $m=[regex]::Match($url,[regex]::Escape($enc)+'=([^&]+)')
 if($m.Success){return [uri]::UnescapeDataString(($m.Groups[1].Value -replace '\+',' '))}
 return ''
}
$newCount=0
foreach($item in $plan.products){
 if($item.status -eq 'already_captured' -or $doneIds -contains [string]$item.product_id){continue}
 if($newCount -ge $MaxNewCaptures){break}
 $root=Get-Root;$addr=Get-AddressEdit $root
 if(-not $addr){Write-Output ("BLOCKED {0}: Chrome address bar not found" -f $item.product_id);break}
 $searchUrl=if($item.query_url){[string]$item.query_url}else{'https://partners.coupang.com/#affiliate/ws/link/0/'+[uri]::EscapeDataString([string]$item.query)}
 $addr.SetFocus()
 [System.Windows.Forms.Clipboard]::SetText($searchUrl)
 [System.Windows.Forms.SendKeys]::SendWait('^a')
 [System.Windows.Forms.SendKeys]::SendWait('^v')
 [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
 Start-Sleep -Seconds 5
 Scroll-PageDown
 $root=Get-Root
 $linkButton=$null
 $buttons=Get-ByType $root ([System.Windows.Automation.ControlType]::Button)
 foreach($b in $buttons){if($b.Current.Name -eq '링크 생성' -and -not $b.Current.IsOffscreen){$linkButton=$b;break}}
 if($linkButton){$linkButton.SetFocus();[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')}
 Start-Sleep -Milliseconds 700
 Start-Sleep -Seconds 3
 Scroll-PageDown
 $root=Get-Root;$radio=Get-BlogTagRadio $root
 if($radio){try{$radio.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()}catch{}}
 Start-Sleep -Milliseconds 500
 $root=Get-Root;$tag=Get-BlogTagText $root
 if(-not $tag){Scroll-PageDown;$root=Get-Root;$tag=Get-BlogTagText $root}
 $url=Get-AddressUrl $root
 $href=[regex]::Match([string]$tag,'(?:src|href)="([^"]+)"').Groups[1].Value
 $img=Get-Param $url 'product[image]'
 $alt=[regex]::Match([string]$tag,'alt="([^"]+)"').Groups[1].Value
 $productId=Get-Param $url 'product[productId]'
 $itemId=Get-Param $url 'product[itemId]'
 $vendorItemId=Get-Param $url 'product[vendorItemId]'
 $title=Get-Param $url 'product[title]'
 $price=Get-Param $url 'product[salesPrice]'
 if(-not $price){$price=Get-Param $url 'product[originPrice]'}
 $productImage=Get-Param $url 'product[image]'
 $status=if($href -match '^(https://link\.coupang\.com/|https://coupa\.ng/)' -and ($tag -like '<iframe src=*' -or $tag -like '<a href=*') -and $img -and $url -match '/linkgeneration/PRODUCT/'){ 'CAPTURED' } else { 'NEEDS_REVIEW' }
 $record=[pscustomobject]@{candidate_id=$item.product_id;query=$item.query;result_index=0;product_title=$title;product_id=$productId;item_id=$itemId;vendor_item_id=$vendorItemId;price=$price;affiliate_url=$href;product_image_url=$productImage;official_image_url=$img;image_alt=$alt;official_blog_html_tag=$tag;link_generation_url=$url;status=$status;captured_at_kst=(Get-Date).ToString('yyyy-MM-dd HH:mm:ss')}
 if($status -eq 'CAPTURED'){
  Add-Content -Path $outPath -Value ($record|ConvertTo-Json -Depth 8 -Compress) -Encoding UTF8
  $doneIds+=([string]$item.product_id)
  $plan|ConvertTo-Json -Depth 8|Set-Content -Path $planPath -Encoding UTF8
  $newCount++
 }
 Write-Output ("{0} {1} | {2} | {3} | {4}" -f $status,$item.product_id,$title,$price,$href)
}
Write-Output ("DONE new_captures={0} output={1}" -f $newCount,$outPath)


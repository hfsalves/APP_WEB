[Console]::OutputEncoding=[Text.Encoding]::UTF8
Add-Type @'
using System;using System.IO;using System.Collections.Generic;
public class AF{public string Path;public long Bytes;public string Created,Modified;}
public class AR{
public Dictionary<string,long[]> B=new Dictionary<string,long[]>(StringComparer.OrdinalIgnoreCase),M=new Dictionary<string,long[]>();
public List<AF> Large=new List<AF>();public List<string> Errors=new List<string>(),Apps=new List<string>();public long Files,Bytes,Dirs,ErrorCount,Skipped;
void Bad(string p){ErrorCount++;if(Errors.Count<100)Errors.Add(p);}
void Sum(string k,FileInfo f){if(!B.ContainsKey(k))B[k]=new long[5];var a=B[k];a[0]+=f.Length;a[1]++;var d=f.CreationTime;if(d>=new DateTime(2026,4,14))a[2]+=f.Length;if(d>=new DateTime(2026,7,14))a[3]+=f.Length;if(d>=new DateTime(2026,9,14))a[4]+=f.Length;}
public void Scan(string r){var q=new Stack<string>();q.Push(r);while(q.Count>0){var p=q.Pop();Dirs++;var dn=Path.GetFileName(p).ToLowerInvariant();if(dn=="app_web"||dn=="document_ai"||dn=="document_ai_preprocessed"||dn==".document_ai_cache"||dn.Contains("gr360"))Apps.Add(p);
try{foreach(var e in new DirectoryInfo(p).EnumerateFileSystemInfos()){try{if((e.Attributes&FileAttributes.ReparsePoint)!=0){Skipped++;continue;}if((e.Attributes&FileAttributes.Directory)!=0){q.Push(e.FullName);continue;}var f=(FileInfo)e;var n=f.Length;Files++;Bytes+=n;Sum(r,f);var s=f.FullName.Substring(3).Split('\\');var k=r;for(int i=0;i<Math.Min(s.Length-1,s[0].ToUpper()=="GED"?3:2);i++){k+=(i>0?"\\":"")+s[i];Sum(k,f);}
for(int i=0;i<2;i++){var d=i==0?f.CreationTime:f.LastWriteTime;if(d.Year<2026)continue;var mk=r+"|"+(i==0?"created":"modified")+"|"+d.ToString("yyyy-MM");if(!M.ContainsKey(mk))M[mk]=new long[2];M[mk][0]+=n;M[mk][1]++;}
if(n>=2147483648L)Large.Add(new AF{Path=f.FullName,Bytes=n,Created=f.CreationTime.ToString("o"),Modified=f.LastWriteTime.ToString("o")});}catch{Bad(e.FullName);}}}catch{Bad(p);}}}}
'@
$a=New-Object AR;$start=Get-Date
foreach($r in @('C:\','D:\','E:\')){$a.Scan($r)}
@{Started=$start.ToString('o');Finished=(Get-Date).ToString('o');Buckets=$a.B;Months=$a.M;Files=$a.Files;Bytes=$a.Bytes;Directories=$a.Dirs;Errors=$a.Errors;ErrorCount=$a.ErrorCount;SkippedReparse=$a.Skipped;AppDirectories=$a.Apps;Largest=@($a.Large|Sort-Object Bytes -Descending|Select-Object -First 60)}|ConvertTo-Json -Depth 5 -Compress

const OLD_RELEASE = 'https://github.com/wssfk12138/english-multiple-choice-practice-machine/releases/download/question-banks-v1.2.0/'
const BANK_RELEASES = 'https://github.com/wssfk12138/english-question-banks/releases/download/'
export const OFFICIAL_CATALOG = 'https://raw.githubusercontent.com/wssfk12138/english-question-banks/main/question-bank-catalog.json'
/**
 * 规范地址不可达时的同源备用入口（2026-09-28 实测三条都可读且内容一致）：
 * 独立题库仓库的固定 Release 目录，以及迁移前的旧目录入口（仍在同步维护）。
 * 只追加在代理之后，避免在直连被挡的网络里多等两轮连接超时。
 */
export const OFFICIAL_CATALOG_FALLBACKS = [
  BANK_RELEASES + 'question-banks-2026-09-20/question-bank-catalog.json',
  OLD_RELEASE + 'question-bank-catalog.json',
]

// 这里只用于"识别存量官方别名"：老版本把官方默认地址写进了设置，
// 命中即按官方链处理。列表项本身不参与下载，失效的别名保留是为了不误判成第三方地址。
export const LEGACY_OFFICIAL_CATALOGS = [
  OLD_RELEASE + 'question-bank-catalog.json',
  'https://github.com/wssfk12138/english-multiple-choice-practice-machine/releases/latest/download/question-bank-catalog.json',
]
const PROXY_ORIGINS = ['https://ghfast.top/', 'https://gh-proxy.com/']

export function officialDownloadSources(url: string, enabled: boolean): string[] {
  if (!enabled) return [url]
  // Exact catalog or release assets only; never proxy credentials, query strings,
  // path traversal, other repositories or third-party sources.
  const oldAsset = url.startsWith(OLD_RELEASE)
    && /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(url.slice(OLD_RELEASE.length))
  const bankAsset = url.startsWith(BANK_RELEASES)
    && /^question-banks-[A-Za-z0-9][A-Za-z0-9._-]*\/[A-Za-z0-9][A-Za-z0-9._-]*\.esq$/.test(url.slice(BANK_RELEASES.length))
  if (url !== OFFICIAL_CATALOG && !oldAsset && !bankAsset) return [url]
  return [url, ...PROXY_ORIGINS.map(origin => origin + url)]
}

export async function withOfficialDownloadFallback<T>(
  url: string, enabled: boolean, download: (source: string) => Promise<T>,
): Promise<T> {
  const sources = officialDownloadSources(url, enabled)
  for (let index = 0; index < sources.length; index += 1) {
    try { return await download(sources[index]!) }
    catch (error) { if (index === sources.length - 1) throw error }
  }
  throw new Error('没有可用的下载地址')
}

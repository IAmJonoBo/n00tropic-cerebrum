export function mountApp(selector: string) {
  const el = document.querySelector(selector)
  if (!el) return
  el.innerHTML = `<h1>It works</h1><p>Edit apps/web/src/*</p>`
}

import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

const ignoredDirectories = new Set([
  '.git',
  'dist',
  'node_modules',
  'playwright-report',
  'reports',
  'test-results',
])

function findMarkdownFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name)
    if (entry.isDirectory()) {
      return ignoredDirectories.has(entry.name) ? [] : findMarkdownFiles(path)
    }
    return entry.isFile() && entry.name.endsWith('.md') ? [path] : []
  })
}

const localLinkPattern = /!?\[[^\]]*\]\(([^)]+)\)/g
const markdownFiles = findMarkdownFiles(process.cwd())
const brokenLinks = []

for (const file of markdownFiles) {
  const content = readFileSync(file, 'utf8')
  for (const match of content.matchAll(localLinkPattern)) {
    const target = match[1].split('#')[0]
    if (!target || /^(?:https?:|mailto:|#)/.test(target)) {
      continue
    }
    if (!existsSync(resolve(dirname(file), target))) {
      brokenLinks.push(`${file} -> ${match[1]}`)
    }
  }
}

if (brokenLinks.length > 0) {
  console.error('Broken local Markdown links:')
  brokenLinks.forEach((link) => console.error(`- ${link}`))
  process.exit(1)
}

console.log(
  `Validated ${markdownFiles.length} Markdown files: all local links resolve.`,
)

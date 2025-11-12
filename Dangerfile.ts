import { danger, fail, warn, message } from "danger";

const mdChanged: string[] = danger.git.modified_files.filter(
  (f: string) => f.endsWith(".adoc") || f.endsWith(".md"),
);

async function checkReviewDates() {
  if (mdChanged.length) {
    message(`Docs changed: ${mdChanged.length} files`);
    // Encourage review date updates when docs change
    for (const f of mdChanged) {
      const file = f as string;
      const content = await danger.github.utils.fileContents(file);
      if (!/^:reviewed:\s?\d{4}-\d{2}-\d{2}/m.test(content)) {
        warn(`Missing :reviewed: date in ${f}`);
      }
      if (!/^:page-tags:\s?.+/m.test(content)) {
        warn(`Missing :page-tags: metadata in ${f}`);
      }
    }
  }
}

checkReviewDates();

import { danger, fail, warn, message } from "danger";

const mdChanged = danger.git.modified_files.filter(f => f.endsWith(".adoc") || f.endsWith(".md"));

async function checkReviewDates() {
  if (mdChanged.length) {
    message(`Docs changed: ${mdChanged.length} files`);
    // Encourage review date updates when docs change
    for (const f of mdChanged) {
      const content = await danger.github.utils.fileContents(f);
      if (!/^:reviewed:\s?\d{4}-\d{2}-\d{2}/m.test(content)) {
        warn(`Missing :reviewed: date in ${f}`);
      }
    }
  }
}

checkReviewDates();

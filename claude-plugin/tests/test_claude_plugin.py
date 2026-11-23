"""Tests for the skills-only Claude Code port of Axiom Agent (stdlib unittest).

They read files only: no network, no writes, nothing under ~/.claude.
"""
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
CLAUDE = os.path.dirname(HERE)
REPO = os.path.dirname(CLAUDE)
PLUGIN = os.path.join(CLAUDE, "axiom-agent")
DOCTRINE = os.path.join(REPO, "DOCTRINE.md")
SHIPPED_DOCTRINE = os.path.join(REPO, "axiom_agent", "DOCTRINE.md")
DOCTRINE_SKILL = os.path.join(PLUGIN, "skills", "doctrine", "SKILL.md")
STATUS_SKILL = os.path.join(PLUGIN, "skills", "doctrine-status", "SKILL.md")

# Hermes enforcer names (as written in DOCTRINE.md) -> Claude Code plugin names.
CLAUDE_NAME = {
    "hermes-axioma": "axiom-axioma",
    "hermes-gatekeeper": "axiom-gatekeeper",
    "standing": "axiom-standing",
    "tripwire": "axiom-tripwire",
    "handydandy": "axiom-handydandy",
}
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]


def slurp(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def frontmatter(text):
    assert text.startswith("---\n"), "frontmatter must be the first line"
    block, _, body = text[4:].partition("\n---\n")
    fields = {}
    for line in block.splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, body


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.plugin = json.loads(slurp(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))
        self.market = json.loads(slurp(os.path.join(REPO, ".claude-plugin", "marketplace.json")))

    def test_identity(self):
        p = self.plugin
        self.assertEqual(p["name"], "axiom-agent")
        self.assertEqual(p["displayName"], "Axiom Agent")
        self.assertEqual(p["version"], "0.1.0")
        self.assertEqual(p["author"], {"name": "Deploy Axiom"})
        self.assertEqual(p["license"], "MIT")
        self.assertEqual(p["homepage"], p["repository"])
        self.assertTrue(p["repository"].startswith("https://github.com/"))
        self.assertTrue(p["repository"].endswith("/hermes-axiom-agent"))

    def test_icon_present_and_png(self):
        icon = os.path.join(PLUGIN, ".claude-plugin", "icon.png")
        self.assertEqual(self.plugin["icon"], "./.claude-plugin/icon.png")
        with open(icon, "rb") as handle:
            self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")

    def test_marketplace_points_at_plugin(self):
        self.assertEqual(self.market["name"], "deploy-axiom-agent")
        (entry,) = self.market["plugins"]
        self.assertEqual(entry["name"], self.plugin["name"])
        self.assertEqual(entry["source"], "./claude-plugin/axiom-agent")
        self.assertTrue(os.path.isdir(os.path.join(REPO, entry["source"][2:])))

    def test_manifest_declares_no_executable_component(self):
        for key in ("hooks", "mcpServers", "lspServers", "monitors", "commands",
                    "agents", "channels", "types", "workflows", "outputStyles"):
            self.assertNotIn(key, self.plugin)


class SkillsOnlyTests(unittest.TestCase):
    def test_no_executable_components_on_disk(self):
        found = []
        for root, dirs, files in os.walk(PLUGIN):
            for name in dirs + files:
                rel = os.path.relpath(os.path.join(root, name), PLUGIN)
                found.append(rel)
        allowed = {
            ".claude-plugin", ".claude-plugin/plugin.json", ".claude-plugin/icon.png",
            "LICENSE", "README.md", "skills", "skills/doctrine", "skills/doctrine/SKILL.md",
            "skills/doctrine-status", "skills/doctrine-status/SKILL.md",
        }
        self.assertEqual(set(found) - allowed, set())
        for forbidden in ("hooks", "scripts", "mods", ".mcp.json", "commands", "agents"):
            self.assertNotIn(forbidden, found)

    def test_skill_frontmatter_uses_only_portable_fields(self):
        portable = {"name", "description", "license", "compatibility", "metadata", "allowed-tools",
                    "disable-model-invocation"}
        for path in (DOCTRINE_SKILL, STATUS_SKILL):
            fields, _ = frontmatter(slurp(path))
            self.assertLessEqual(set(fields), portable, path)
            self.assertIn("description", fields)
            self.assertNotIn("allowed-tools", fields, "no pre-approved tools")
            self.assertLessEqual(len(fields["description"]), 1536)

    def test_skill_names_match_folders(self):
        for path, name in ((DOCTRINE_SKILL, "doctrine"), (STATUS_SKILL, "doctrine-status")):
            fields, _ = frontmatter(slurp(path))
            self.assertEqual(fields["name"], name)
            self.assertEqual(os.path.basename(os.path.dirname(path)), name)

    def test_status_skill_is_user_invoked_only(self):
        fields, _ = frontmatter(slurp(STATUS_SKILL))
        self.assertEqual(fields["disable-model-invocation"], "true")

    def test_skills_never_inject_shell_output(self):
        for path in (DOCTRINE_SKILL, STATUS_SKILL):
            text = slurp(path)
            self.assertIsNone(re.search(r"^!`|```!", text, re.M), path)

    def test_no_private_data_in_plugin_files(self):
        # Literals are split so this file does not contain what it searches for.
        home, owner = "/Us" + "ers/", "percy" + "keith"
        pattern = re.compile(re.escape(home) + "|" + owner + r"|@(?!deploy-axiom-agent\b)[\w.-]+\.(com|org|net)|sk-[A-Za-z0-9]{10,}")
        for root, _, files in os.walk(PLUGIN):
            for name in files:
                if name.endswith(".png"):
                    continue
                path = os.path.join(root, name)
                self.assertIsNone(pattern.search(slurp(path)), path)


class DoctrineTextTests(unittest.TestCase):
    def test_repo_copies_identical(self):
        self.assertEqual(slurp(DOCTRINE), slurp(SHIPPED_DOCTRINE))

    def test_skill_contains_published_doctrine_verbatim(self):
        self.assertIn(slurp(DOCTRINE), slurp(DOCTRINE_SKILL))

    def test_skill_doctrine_is_a_suffix_after_one_preface(self):
        _, body = frontmatter(slurp(DOCTRINE_SKILL))
        self.assertTrue(body.endswith(slurp(DOCTRINE)))
        preface = body[: -len(slurp(DOCTRINE))]
        self.assertEqual(preface.count("# The Axiom Doctrine"), 0)

    def test_nine_articles_in_order(self):
        text = slurp(DOCTRINE_SKILL)
        heads = re.findall(r"^## (I|II|III|IV|V|VI|VII|VIII|IX)\. ", text, re.M)
        self.assertEqual(heads, ROMAN)


class StatusTableTests(unittest.TestCase):
    def doctrine_enforcers(self):
        """Roman numeral -> set of Claude plugin names, derived from DOCTRINE.md."""
        text = slurp(DOCTRINE)
        out = {}
        for match in re.finditer(r"^## ([IVX]+)\. .*?\n(.*?)\*Enforced by: (.*?)\.\*$", text, re.M | re.S):
            numeral, line = match.group(1), match.group(3)
            names = {CLAUDE_NAME[n] for n in CLAUDE_NAME if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(n), line)}
            out[numeral] = names
        return out

    def status_table(self):
        rows = {}
        for line in slurp(STATUS_SKILL).splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[0] in ROMAN:
                names = set() if cells[2].startswith("none") else {n.strip() for n in cells[2].split(",")}
                rows[cells[0]] = names
        return rows

    def test_table_matches_doctrine_enforcers(self):
        expected = self.doctrine_enforcers()
        self.assertEqual(sorted(expected), sorted(ROMAN))
        self.assertEqual(self.status_table(), expected)

    def test_doctrine_only_articles_and_ceiling(self):
        table = self.status_table()
        self.assertEqual({k for k, v in table.items() if not v}, {"I", "II", "IX"})
        self.assertEqual(sum(1 for v in table.values() if v), 6)

    def test_status_skill_states_limits(self):
        text = slurp(STATUS_SKILL)
        for phrase in ("enforces nothing itself", "not a security claim", "Unknown state is ADVISED",
                       "claude plugin list --json", "exactly one of these names"):
            self.assertIn(phrase, text)


class ReadmeTests(unittest.TestCase):
    def test_readme_has_install_lines_and_known_gaps(self):
        text = slurp(os.path.join(PLUGIN, "README.md"))
        self.assertIn("claude plugin install axiom-agent@deploy-axiom-agent", text)
        self.assertIn("## Known gaps", text)
        self.assertIn("No per-turn injection", text)

    def test_readme_makes_no_certification_claims(self):
        text = slurp(os.path.join(PLUGIN, "README.md")).lower()
        for word in ("certified", "guarantee", "bulletproof"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()

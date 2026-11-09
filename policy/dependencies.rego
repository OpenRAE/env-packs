package main

import rego.v1

pip_calls := [{"file":c.file,"job":c.job,"args":array.slice(c.args,i+2,count(c.args))} |
	some c in input.commands
	some i,arg in c.args
	regex.match(`(^|/)pip3?$`,arg)
	c.args[i+1] == "install"
]
editable(args) if { some arg in args; arg in {"-e","--editable"} }
safe_source(source) if { not regex.match(`^(git|svn|hg|bzr)`,source); not contains(source,"://"); not regex.match("[$`\\\\]",source) }
safe_source(source) if regex.match(`^git(\+(https?|ssh|git))?://.*@[a-fA-F0-9]{40}(#egg=.*)?$`,source)
pip_pinned(args) if { not editable(args); "--require-hashes" in args }
pip_pinned(args) if {
	editable(args)
	"--no-deps" in args
	every i,arg in args { editable_source(args,i,arg) }
}
editable_source(args,i,arg) if not arg in {"-e","--editable"}
editable_source(args,i,arg) if { arg in {"-e","--editable"}; safe_source(args[i+1]) }
pip_pinned(args) if {
	not editable(args)
	count([a | some a in args; endswith(a,".whl")])>0
	every a in args { wheel_or_flag(a) }
}
wheel_or_flag(a) if startswith(a,"-")
wheel_or_flag(a) if endswith(a,".whl")
valid_pip_pins if { count(pip_calls)>0; every c in pip_calls { pip_pinned(c.args) } }
violations contains "dependency.pip-pins" if not valid_pip_pins

lock_rows(text) := [trim_space(row) |
	some row in split(replace(text,"\\\n"," "),"\n")
	trim_space(row) != ""
	not startswith(trim_space(row),"#")
]
locks := {n:v | some n,v in input.text; startswith(n,"requirements/"); endswith(n,".txt")}
lock_pins(text) := {lower(replace(m[1],"_","-")):m[2] | some row in lock_rows(text); some m in regex.find_all_string_submatch_n(`^([A-Za-z0-9._-]+)(?:\[[A-Za-z0-9._,-]+\])?==([^\s,\\]+)`,row,-1)}
all_pins := {n:lock_pins(v) | some n,v in locks}
valid_lock_files if {
	count(locks)>0
	every _,text in locks {
		rows := lock_rows(text)
		count(rows)>0
		every r in rows {
			regex.match(`^[A-Za-z0-9._-]+(?:\[[A-Za-z0-9._,-]+\])?==[^\s,\\]+\s`,r)
			regex.match(`--hash=sha256:[0-9a-f]{64}`,r)
		}
	}
}
violations contains "dependency.lock-files" if not valid_lock_files

references(c) := {c.args[i+1] | some i,arg in c.args; arg in {"-r","--requirement"}}
valid_references if {
	every c in pip_calls {
		every i,arg in c.args { reference_valid(c.args,i,arg) }
	}
}
reference_valid(args,i,arg) if not arg in {"-r","--requirement"}
reference_valid(args,i,arg) if { arg in {"-r","--requirement"}; args[i+1] in object.keys(input.text) }
violations contains "dependency.references" if not valid_references

compatible(a,b) if a.file != b.file
compatible(a,b) if a.job != b.job
compatible(a,b) if {
	every first in references(a) {
		every second in references(b) {
			x := all_pins[first]
			y := all_pins[second]
			every pkg in object.keys(x) & object.keys(y) { x[pkg] == y[pkg] }
		}
	}
}
valid_coinstalled if { every a in pip_calls { every b in pip_calls { compatible(a,b) } } }
violations contains "dependency.co-installed" if not valid_coinstalled

normalized(v) := concat(".", array.concat(parts, array.slice(["0","0","0"],0,3-count(parts)))) if parts := split(v,".")
version_at_least(a,b) if semver.compare(normalized(a),normalized(b))>=0
valid_floors if {
	version_at_least(all_pins["requirements/pip-audit.txt"].pip,"26.2.0")
	version_at_least(all_pins["requirements/pip-audit.txt"].msgpack,"1.2.3")
	version_at_least(all_pins["requirements/pip-audit.txt"].certifi,"2026.10.19")
	version_at_least(all_pins["requirements/docs.txt"].certifi,"2026.10.19")
}
violations contains "dependency.floors" if not valid_floors

valid_update_owners if {
	u := doc(".github/dependabot.yml").updates
	go := [e | some e in u; e["package-ecosystem"] == "gomod"]
	count(go)==1
	go[0].directory == "/"
	go[0]["target-branch"] == "go-cutover"
	go[0]["commit-message"].prefix == "build"
	count([e | some e in u; e["package-ecosystem"] == "pip"; e.directory == "/requirements"])==1
}
violations contains "dependency.update-owners" if not valid_update_owners

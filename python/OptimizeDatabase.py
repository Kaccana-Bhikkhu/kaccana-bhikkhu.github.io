import re, sys

def firstLetterUp(string):
	return string[0].upper() + string[1:]
def firstLetterLow(string):
	if string.isupper(): return string
	return string[0].lower() + string[1:]

def convertKey(key):
	latinKey = key.replace("ā", "a")
	words = list(map(firstLetterUp, re.split("[_\- ]", latinKey)))
	words[0] = firstLetterLow(words[0])
	return "".join(words)

def stripKey(key):
	return '"' + convertKey(key.group(1)) + '":'

def convertFile(path, out):
	f = open(path, "r")
	lines = []
	keyPattern = "\"([^\"]+)\"\\s*:"
	
	for line in f:
		convertedLine = re.sub(keyPattern, stripKey, line)
		lines.append(convertedLine)
	f.close()

	fw = open(out, "w")
	fw.writelines(lines)
	fw.close()

print(convertFile(sys.argv[1], sys.argv[2]))
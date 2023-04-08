"""Quick script to camel case database fields and rename question to excerpt."""

import re, json, os

with open('CamelCaseTranslation.json', 'r', encoding='utf-8') as file: 
        camelCaseTranslation = json.load(file)

singleQuote = "'"
doubleQuote = '"'

substitutions = {}
for key, camelCaseKey in camelCaseTranslation.items():
    substitutions[re.escape(singleQuote + key + singleQuote)] = re.escape(singleQuote + camelCaseKey + singleQuote)
    substitutions[re.escape(doubleQuote + key + doubleQuote)] = re.escape(doubleQuote + camelCaseKey + doubleQuote)

substitutions = {}

print(len(camelCaseTranslation),len(substitutions))
print(len(substitutions),substitutions)

with open('Substitutions.json','w',encoding='utf-8') as file:
     json.dump(substitutions,file,ensure_ascii=False, indent='\t')

fileList = next(os.walk('sources'), (None, None, []))[2]

for fileName in fileList:
    print(fileName)
    with open(os.path.join('sources',fileName)) as source, open(os.path.join('..','..','python',fileName),'w') as dest:
        for n,line in enumerate(source):
            
            if '#NoCamelCase' not in line:
                for match,replace in substitutions.items():
                    changedLine = re.sub(match,replace,line)
                    if changedLine != line:
                        print(n,replace,changedLine,end='')
                    line = changedLine
            
            print(line,end='',file=dest)
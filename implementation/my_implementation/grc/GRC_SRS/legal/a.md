simons@IPS-DEV001:~/Coding/FIMS/frontend$ docker compose logs -f
fims-staff-portal  | 
fims-staff-portal  | > vite_react_shadcn_ts@0.0.0 dev:staff
fims-staff-portal  | > vite --config apps/staff-portal/vite.config.ts --host 0.0.0.0 --port 3000
fims-staff-portal  | 
fims-staff-portal  | Re-optimizing dependencies because lockfile has changed
fims-staff-portal  | 
fims-staff-portal  |   VITE v5.4.19  ready in 551 ms
fims-staff-portal  | 
fims-staff-portal  |   ➜  Local:   http://localhost:3000/
fims-staff-portal  |   ➜  Network: http://172.31.0.26:3000/
fims-staff-portal  | Error:   Failed to scan for dependencies from entries:
fims-staff-portal  |   /app/apps/staff-portal/index.html
fims-staff-portal  | 
fims-staff-portal  |   ✘ [ERROR] Multiple exports with the same name "FCCSuingCaseDetailPage"
fims-staff-portal  | 
fims-staff-portal  |     apps/staff-portal/src/pages/grc/legal/FCCSuingCaseDetailPage.tsx:364:16:
fims-staff-portal  |       364 │ export function FCCSuingCaseDetailPage() {
fims-staff-portal  |           ╵                 ~~~~~~~~~~~~~~~~~~~~~~
fims-staff-portal  | 
fims-staff-portal  |   The name "FCCSuingCaseDetailPage" was originally exported here:
fims-staff-portal  | 
fims-staff-portal  |     apps/staff-portal/src/pages/grc/legal/FCCSuingCaseDetailPage.tsx:35:16:
fims-staff-portal  |       35 │ export function FCCSuingCaseDetailPage() {
fims-staff-portal  |          ╵                 ~~~~~~~~~~~~~~~~~~~~~~
fims-staff-portal  | 
fims-staff-portal  | 
fims-staff-portal  | ✘ [ERROR] The symbol "FCCSuingCaseDetailPage" has already been declared
fims-staff-portal  | 
fims-staff-portal  |     apps/staff-portal/src/pages/grc/legal/FCCSuingCaseDetailPage.tsx:364:16:
fims-staff-portal  |       364 │ export function FCCSuingCaseDetailPage() {
fims-staff-portal  |           ╵                 ~~~~~~~~~~~~~~~~~~~~~~
fims-staff-portal  | 
fims-staff-portal  |   The symbol "FCCSuingCaseDetailPage" was originally declared here:
fims-staff-portal  | 
fims-staff-portal  |     apps/staff-portal/src/pages/grc/legal/FCCSuingCaseDetailPage.tsx:35:16:
fims-staff-portal  |       35 │ export function FCCSuingCaseDetailPage() {
fims-staff-portal  |          ╵                 ~~~~~~~~~~~~~~~~~~~~~~
fims-staff-portal  | 
fims-staff-portal  |   Duplicate top-level function declarations are not allowed in an ECMAScript module. This file is considered to be an ECMAScript module because of the "export" keyword here:
fims-staff-portal  | 
fims-staff-portal  |     apps/staff-portal/src/pages/grc/legal/FCCSuingCaseDetailPage.tsx:364:0:
fims-staff-portal  |       364 │ export function FCCSuingCaseDetailPage() {
fims-staff-portal  |           ╵ ~~~~~~
fims-staff-portal  | 
fims-staff-portal  | 
fims-staff-portal  |     at failureErrorWithLog (/app/node_modules/esbuild/lib/main.js:1472:15)
fims-staff-portal  |     at /app/node_modules/esbuild/lib/main.js:945:25
fims-staff-portal  |     at runOnEndCallbacks (/app/node_modules/esbuild/lib/main.js:1315:45)
fims-staff-portal  |     at buildResponseToResult (/app/node_modules/esbuild/lib/main.js:943:7)
fims-staff-portal  |     at /app/node_modules/esbuild/lib/main.js:955:9
fims-staff-portal  |     at new Promise (<anonymous>)
fims-staff-portal  |     at requestCallbacks.on-end (/app/node_modules/esbuild/lib/main.js:954:54)
fims-staff-portal  |     at handleRequest (/app/node_modules/esbuild/lib/main.js:647:17)
fims-staff-portal  |     at handleIncomingPacket (/app/node_modules/esbuild/lib/main.js:672:7)
fims-staff-portal  |     at Socket.readFromStdout (/app/node_modules/esbuild/lib/main.js:600:7)
fims-staff-portal  | Error processing file apps/staff-portal/src/pages/grc/legal/FCCSuingCaseDetailPage.tsx: SyntaxError: Identifier 'FCCSuingCaseDetailPage' has already been declared. (364:16)
fims-staff-portal  |     at constructor (/app/node_modules/@babel/parser/lib/index.js:367:19)
fims-staff-portal  |     at TypeScriptParserMixin.raise (/app/node_modules/@babel/parser/lib/index.js:6624:19)
fims-staff-portal  |     at TypeScriptScopeHandler.checkRedeclarationInScope (/app/node_modules/@babel/parser/lib/index.js:1646:19)
fims-staff-portal  |     at TypeScriptScopeHandler.declareName (/app/node_modules/@babel/parser/lib/index.js:1612:12)
fims-staff-portal  |     at TypeScriptScopeHandler.declareName (/app/node_modules/@babel/parser/lib/index.js:4909:11)
fims-staff-portal  |     at TypeScriptParserMixin.registerFunctionStatementId (/app/node_modules/@babel/parser/lib/index.js:13542:16)
fims-staff-portal  |     at TypeScriptParserMixin.registerFunctionStatementId (/app/node_modules/@babel/parser/lib/index.js:9229:13)
fims-staff-portal  |     at TypeScriptParserMixin.parseFunction (/app/node_modules/@babel/parser/lib/index.js:13526:12)
fims-staff-portal  |     at TypeScriptParserMixin.parseFunctionStatement (/app/node_modules/@babel/parser/lib/index.js:13201:17)
fims-staff-portal  |     at TypeScriptParserMixin.parseStatementContent (/app/node_modules/@babel/parser/lib/index.js:12867:21) {
fims-staff-portal  |   code: 'BABEL_PARSER_SYNTAX_ERROR',
fims-staff-portal  |   reasonCode: 'VarRedeclaration',
fims-staff-portal  |   loc: Position { line: 364, column: 16, index: 15681 },
fims-staff-portal  |   pos: 15681,
fims-staff-portal  |   syntaxPlugin: undefined
fims-staff-portal  | }



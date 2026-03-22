# Legal Module — Frontend Implementation Order (Quick Reference)

> Use this file to track progress and tell the agent which step/item to implement next.
> Full specs for each item are in `Legal_Module_Frontend_Implementation_Plan.md` → Phase 16.

---

## Step 1 — Foundation Layer

- [ ] 1. `types/legal.ts` — all type definitions and status maps
- [ ] 2. `hooks/legalKeys.ts` — query key factories
- [ ] 3. `services/legalService.ts` — all API functions
- [ ] 4. `hooks/useLegalPermissions.ts` — permission hook (30 codes)
- [ ] 5. `hooks/useLegalConfig.ts` — lookup hooks
- [ ] 6. `hooks/useLegalWorkflows.ts` — workflow status/history hooks
- [ ] 7. `hooks/useLegalDashboard.ts` — dashboard stats hook
- [ ] 8. `hooks/useLegalAuditLog.ts` — audit log query hook
- [ ] 9. `components/grc/legal/LegalStatusBadge.tsx` — shared status badge
- [ ] 10. `components/grc/legal/ActivityLogSection.tsx` — reusable audit log card
- [ ] 11. `components/grc/legal/ApprovalChainDisplay.tsx` — reusable approval chain
- [ ] 12. `components/grc/legal/UserDisplay.tsx` — UUID → user name display
- [ ] 13. Routing: add Legal routes to `App.tsx`
- [ ] 14. Sidebar: add Legal nav section to service layout config

---

## Step 2 — Governance Structure

- [ ] 15. `hooks/useCommitteeTypes.ts`
- [ ] 16. `components/grc/legal/CreateCommitteeTypeDialog.tsx`
- [ ] 17. `pages/grc/legal/CommitteeTypesPage.tsx`
- [ ] 18. `hooks/useGoverningBodies.ts`
- [ ] 19. `hooks/useMembers.ts`
- [ ] 20. `components/grc/legal/CreateGoverningBodyDialog.tsx`
- [ ] 21. `components/grc/legal/CreateMemberDialog.tsx`
- [ ] 22. `pages/grc/legal/GoverningBodiesPage.tsx`
- [ ] 23. `pages/grc/legal/GoverningBodyDetailPage.tsx`
- [ ] 24. `pages/grc/legal/MembersPage.tsx`

---

## Step 3 — Determinations

- [ ] 25. `hooks/useSubmissions.ts`
- [ ] 26. `components/grc/legal/CreateSubmissionDialog.tsx`
- [ ] 27. `pages/grc/legal/SubmissionsPage.tsx`
- [ ] 28. `pages/grc/legal/SubmissionDetailPage.tsx`

---

## Step 4 — Meeting Governance

- [ ] 29. `hooks/useLegalMeetings.ts`
- [ ] 30. `hooks/useMeetingAgenda.ts`
- [ ] 31. `hooks/useMeetingParticipants.ts`
- [ ] 32. `hooks/useMeetingDirectives.ts`
- [ ] 33. `hooks/useMinutes.ts`
- [ ] 34. `hooks/useResolutions.ts`
- [ ] 35. `components/grc/legal/CreateMeetingDialog.tsx`
- [ ] 36. `components/grc/legal/MeetingAgendaSection.tsx`
- [ ] 37. `components/grc/legal/RecordAgendaOutcomeDialog.tsx`
- [ ] 38. `components/grc/legal/MeetingParticipantsSection.tsx`
- [ ] 39. `components/grc/legal/ConflictDeclarationDialog.tsx`
- [ ] 40. `components/grc/legal/CreateDirectiveDialog.tsx`
- [ ] 41. `components/grc/legal/CloseDirectiveDialog.tsx`
- [ ] 42. `components/grc/legal/FullyCloseDirectiveDialog.tsx`
- [ ] 43. `components/grc/legal/MattersArisingSection.tsx`
- [ ] 44. `components/grc/legal/CreateMinutesDialog.tsx`
- [ ] 45. `components/grc/legal/RescheduleMeetingDialog.tsx`
- [ ] 46. `components/grc/legal/EditResolutionDialog.tsx`
- [ ] 47. `pages/grc/legal/LegalMeetingsPage.tsx`
- [ ] 48. `pages/grc/legal/LegalMeetingDetailPage.tsx`
- [ ] 49. `pages/grc/legal/DirectivesPage.tsx`
- [ ] 50. `pages/grc/legal/DirectiveDetailPage.tsx`
- [ ] 51. `pages/grc/legal/MinutesPage.tsx`
- [ ] 52. `pages/grc/legal/MinutesDetailPage.tsx`
- [ ] 53. `pages/grc/legal/ResolutionsPage.tsx`

---

## Step 5 — Litigation: FCC Sued (Defendant)

- [ ] 54. `hooks/useCaseDefendant.ts`
- [ ] 55. `hooks/useLitigationDirectives.ts`
- [ ] 56. `hooks/useFilings.ts`
- [ ] 57. `hooks/useResponses.ts`
- [ ] 58. `hooks/useHearings.ts`
- [ ] 59. `hooks/useSettlements.ts`
- [ ] 60. `hooks/useJudgments.ts`
- [ ] 61. `hooks/useFinancials.ts`
- [ ] 62. `hooks/useLitigationTasks.ts`
- [ ] 63. `components/grc/legal/CreateCaseDefendantDialog.tsx`
- [ ] 64. `components/grc/legal/HoldCaseDialog.tsx`
- [ ] 65. `components/grc/legal/ResumeCaseDialog.tsx`
- [ ] 66. `components/grc/legal/DGDirectiveDecisionDialog.tsx`
- [ ] 67. `components/grc/legal/CaseDirectivesSection.tsx`
- [ ] 68. `components/grc/legal/CreateFilingDialog.tsx`
- [ ] 69. `components/grc/legal/CaseFilingsSection.tsx`
- [ ] 70. `components/grc/legal/CreateResponseDialog.tsx`
- [ ] 71. `components/grc/legal/CaseResponsesSection.tsx`
- [ ] 72. `components/grc/legal/CreateHearingDialog.tsx`
- [ ] 73. `components/grc/legal/HearingReportDialog.tsx`
- [ ] 74. `components/grc/legal/CaseHearingsSection.tsx`
- [ ] 75. `components/grc/legal/CreateSettlementDialog.tsx`
- [ ] 76. `components/grc/legal/CaseSettlementSection.tsx`
- [ ] 77. `components/grc/legal/RecordJudgmentDialog.tsx`
- [ ] 78. `components/grc/legal/CaseJudgmentSection.tsx`
- [ ] 79. `components/grc/legal/FinancialRecordDialog.tsx`
- [ ] 80. `components/grc/legal/CaseFinancialsSection.tsx`
- [ ] 81. `components/grc/legal/CreateLitigationTaskDialog.tsx`
- [ ] 82. `components/grc/legal/CaseTasksSection.tsx`
- [ ] 83. `components/grc/legal/CaseReportSection.tsx`
- [ ] 84. `pages/grc/legal/FCCSuedCasesPage.tsx`
- [ ] 85. `pages/grc/legal/FCCSuedCaseDetailPage.tsx`

---

## Step 6 — Litigation: FCC Suing (Plaintiff)

- [ ] 86. `hooks/useCasePlaintiff.ts`
- [ ] 87. `components/grc/legal/CreateCasePlaintiffDialog.tsx`
- [ ] 88. `components/grc/legal/BreachReportIntakeDialog.tsx`
- [ ] 89. `pages/grc/legal/FCCSuingCasesPage.tsx`
- [ ] 90. `pages/grc/legal/FCCSuingCaseDetailPage.tsx`

---

## Step 7 — Public Register

- [ ] 91. `hooks/usePublicDecisions.ts`
- [ ] 92. `components/grc/legal/CreatePublicDecisionDialog.tsx`
- [ ] 93. `pages/grc/legal/PublicRegisterPage.tsx`
- [ ] 94. `pages/grc/legal/PublicDecisionDetailPage.tsx`

---

## Step 8 — Dashboard

- [ ] 95. `pages/grc/legal/LegalDashboardPage.tsx`

---

## Step 9 — Notification Integration

- [ ] 96. Notification bell/inbox in shared header/navigation

---

## Step 10 — Integration Testing & Polish

- [ ] 97. E2E Governance flow
- [ ] 98. E2E Litigation (Sued)
- [ ] 99. E2E Litigation (Suing)
- [ ] 100. RBAC matrix: all 6 roles × all entity permissions
- [ ] 101. Workflow console integration for all 10 workflow entities
- [ ] 102. Hold/Resume CTAs + on-hold banner
- [ ] 103. Archive/Unarchive + "Show Archived" toggle
- [ ] 104. DG directive approval flow
- [ ] 105. My Cases filtering
- [ ] 106. Meeting number config (prefix + format)
- [ ] 107. Auto-created task "System" badge
- [ ] 108. Notification bell: unread count, mark-as-read, inbox drawer
- [ ] 109. Start Meeting time guard
- [ ] 110. Invitee read-only directives
- [ ] 111. Assigned-user directive closure check
- [ ] 112. Status badge colors (on_hold amber, pending_dg_approval purple)
- [ ] 113. Audit history display on all detail pages
- [ ] 114. Approval chain display (filings, settlements, judgments)
- [ ] 115. Quorum counter + RSVP tally
- [ ] 116. Conflict of interest declaration
- [ ] 117. Appeal auto-creation (Notice of Appeal + deadline task)
- [ ] 118. Read-only closed cases
- [ ] 119. CloseDirectiveDialog validation
- [ ] 120. FullyCloseDirectiveDialog — disappears from Matters Arising
- [ ] 121. MeetingAgendaSection SmartSelect filter
- [ ] 122. CreateMeetingDialog SmartSelect filter
- [ ] 123. ResolutionsPage empty state + no Create button
- [ ] 124. CaseFinancialsSection Corporate Service links
- [ ] 125. Responsive layout verification
- [ ] 126. Digital signature display on approvals

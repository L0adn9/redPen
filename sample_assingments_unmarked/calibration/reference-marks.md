# Reference marks (marked by Claude, before any Gemini Examiner run)

These are an independent second marker's marks, **not lecturer marks**. Use them only as a cross-model check and say so.
Grade scale: A+ ≥80, A 75–79, B+ 70–74, B 65–69, C+ 60–64, C 50–59, D 40–49, F <40.

## 1. CCP Report (CT074-3-2 Concurrent Programming, Report 20%)
Marked: `CCP_Report/S1/answer.docx` = the later version (`ds assignment 2/Concurrent Programming Report.docx`, edited 26 Oct).
The earlier version (25 Oct) was reworded into this one, and the rewording introduced several factual slips (see below).

| Criterion | Max | Mark | Why |
|---|---|---|---|
| Assumptions | 20 | 16 | 8 clear assumptions, each tied to how it is implemented (Table 1). Assumption 5 is garbled ("there are no readiness of passengers"). |
| Safety aspects of the multi-threaded system | 30 | 24 | Hazard table covers race conditions, runway collision, over-capacity, deadlock (Coffman conditions), starvation, visibility and overbooking, each with its protection, plus a run-time Safety recorder. Mostly table form, little explanation of *why* each protection is enough. |
| Justification of coding techniques | 30 | 23 | Strong table: each technique with a reason and a rejected alternative. Lost marks for slips: the "Producer-consumer" paragraph describes priority scheduling instead; "one passenger per terminal" and "individual communications truck" are wrong. |
| Depth of discussion of concurrency concepts | 20 | 15 | Mutual exclusion, atomic CAS, monitor with condition, latch, producer-consumer, priority, happens-before, with code snippets and references (Goetz, Coffman, Ben-Ari). Accurate but short, and two paragraphs lost accuracy in the rewording. |
| **Total** | 100 | **78** | **A** |

Body is about 1,460 words (limit 1,500).

## 2. CCP System (CT074-3-2, System 25%)
Marked from the Java source (`TP088111 CCP/`) and our own runs: compiled with javac and ran seeds 2026, 1, 2, 3.
Each run finished in about 25 s with **all sanity checks passed** (gates empty, peaks ≤ 3 / 1 / 1, 0 safety violations, no deadlock).
The rubric says four criteria are judged from the **video**; I did not watch the video, so those marks use the code and console output instead.

| Criterion | Max | Mark | Why |
|---|---|---|---|
| Coding techniques + comment lines | 20 | 17 | One class per actor, clear Javadoc headers, about 180 comment lines in 983. |
| Java concurrent facilities | 20 | 18 | Fair Semaphore, ReentrantLock + Condition, CompletableFuture, CountDownLatch, BlockingQueue, atomics and LongAdder, each used where it fits. |
| Runs with basic requirements | 20 | 18 | Every basic requirement visible in the output; thread names on every line; no thread acts for another; under 60 s. |
| Additional requirements | 20 | 18 | Concurrent embark/disembark, concurrent cleaning and restocking, exclusive refuel truck, congestion scenario with a MAYDAY plane cleared first, plus own additions (fuel-aware holding, watchdog). Congestion is staged with a 20 s fallback. |
| Explanations with code samples | 20 | 15 | Video not reviewed; marked from the report's code snippets, which are relevant but brief. |
| **Total** | 100 | **86** | **A+** |

## 3. DSTR Lab Work #2, Task 2 only (CT077-3-2, group C++ system, marked individually)
Assumed Hassan's module is **Task 2** (Task 1, 3 and 4 headers name other members; Task 2 has no name). Marked `DSTR_Tasks_1_to_4/Task2.cpp` in the integrated build.
Compiled with `g++ -std=c++17 -Wall -Wextra`: **0 warnings**; menu smoke test runs.

**Part A: code (15)**

| Criterion | Max | Mark | Why |
|---|---|---|---|
| Technical challenges | 3 | 2.5 | Reserves a Task 3 resource before a request goes to Processing; auto-syncs requests when Task 1 finishes a parcel elsewhere (stops a stale head blocking the queue); persistence with ID/sequence restore. |
| Appropriate data structures and algorithms | 3 | 2.5 | Hand-written priority queue as a sorted linked list, stable FIFO for equal priority (O(n) enqueue, O(1) dequeue), plus a linked-list request store. Fits the task; a heap would scale better but is not needed at this size. |
| Functional requirements | 3 | 2.5 | Create (with duplicate/active checks), display active in priority order, next-request rule, process/complete/cancel/return, search, history. Priority rule is fixed by service type, not justified in the code. |
| Code quality | 2 | 1.5 | Readable, modular, good error messages. Thin comments in places; delivered parcels end as "Collected". |
| Individual contribution to the integrated system | 2 | 1.5 | Real integration with Tasks 1, 3 and 4 (status transitions, resource allocation, activity log). |
| Innovation | 2 | 1 | Save/restore and auto-sync are useful extras; nothing beyond that. |
| **Part A total** | 15 | **11.5** | **77% (A)** |

**Part B: face-to-face Q&A (15)**: not markable from the submission. It happens live with the lecturer, so no AI-written submission can earn it. This is a good RedPen example: half of this assessment is AI-resilient by design.

## 4. WAPP Member Module Report (CT050-3-2, Documentation 50%)
Marked `RentSmartKL_Member_Module_Report.docx` against the 5 documentation criteria. The Implementation half (website + presentation) can't be marked from a report.

| Criterion | Max | Mark | Why |
|---|---|---|---|
| Introduction | 10 | 7 | Clear purpose, page/file table, three objectives, in/out of scope. No project schedule, which the brief asks for. |
| Storyboard & Design Documents | 10 | 7 | Use case diagram + table, flow chart for the main feature, major functions. No audience modelling. |
| Design & Modelling | 10 | 7 | Table/column/operation list, 4 wireframes, navigation map with description. Relies on the group ERD instead of showing one. |
| Implementation & Discussion | 10 | 9 | Very thorough: shared helper, every SQL query (parameterised, scoped to the user), transaction for delete, validators table, all 3 CSS types, 31 test cases with 3 bugs found and fixed. |
| Conclusion, Document Styles & Formatting | 10 | 6 | Good summary, lessons and future work. Only 5 references (all web docs); several garbled sentences and body text tagged as headings; a duplicated "Key code" line. |
| **Total** | 50 | **36** | **72% (B+)** |

## 5. RMCT Part 2: Literature Review & Methodology (CT098-3-2, 45%)
**No official rubric was supplied** (only the module descriptor), so I derived 4 criteria from the CLOs; the Examiner gets the same rubric. The 15% presentation is live and not marked.

| Criterion | Max | Mark | Why |
|---|---|---|---|
| Literature review | 35 | 28 | Three domains, mostly 2023–2025 empirical sources, each ends with an explicit gap linked to an objective. Some sentences misstate sources or are garbled ("cognitive leaching", Mollick & Mollick described backwards). |
| Similar systems + gap | 15 | 13 | Three relevant systems, two comparison tables, clear feature gap. |
| Methodology | 35 | 29 | Sequential explanatory mixed methods with an objective-to-method table; Krejcie & Morgan (370 → 450) and G*Power (d = 0.8, 26 per group) are correct; kappa, Cronbach's alpha, SUS/TAM, thematic analysis, PDPA ethics, honest limitations. The "Phase 3" and "Data analysis" paragraphs have swapped content. |
| Academic writing + referencing | 15 | 10 | 29 well-formed APA 7 references. Writing has many paraphrase-style glitches ("III-d stage explanatory mixed", "removal of arms around AI"). |
| **Total** | 100 | **80** | **A+** (borderline) |

## 6. CSLLT SmartSignal (CT073-3-2, individual, 60%)
**No brief or rubric was supplied.** Requirements were reconstructed from the report's cover and structure, and 6 criteria were derived from them; the Examiner gets the same rubric. The NASM source wasn't in the folder, so nothing was run.

| Criterion | Max | Mark | Why |
|---|---|---|---|
| Introduction and background | 10 | 8 | Register and system-call tables, clear project goals, 8 assumptions. |
| Research and critical analysis | 25 | 19 | Good coverage (kernels, FFmpeg AVX-512, malware analysis, Ghidra, Stuxnet/WannaCry/Mirai) and an excellent hands-on reverse-engineering + binary-patching demo on its own binary. But section 2.2.1 "Embedded and Real-Time Systems" is a copy of 2.1, so that topic is missing; some garbled sentences. |
| System design | 15 | 11 | Function table mapped to constructs, phase table, several flowcharts, data design. The phase-model text contradicts the assumptions (pedestrians cross in all-red vs "yellow continues"; emergency "extra amber" vs "all-red"). |
| Implementation of required constructs | 25 | 21 | ADD/SUB, LOOP vs DEC/JNZ (explains the 127-byte LOOP limit), JE/JB/JG jumps, non-blocking input with poll/termios, range-checked input, each with code. |
| Testing, user manual, screenshots | 15 | 13 | 18 test cases with expected/actual, edge cases (Ctrl+C, closed stdin, duplicate requests), full user manual, 10 pages of screenshots. |
| Conclusion, references, presentation | 10 | 6 | The conclusion stops mid-sentence ("adjusting green time depending on"); about 14 APA references; AI declaration included. |
| **Total** | 100 | **78** | **A** |

## 7. MAE Part 2 Group 17 report (CT124-3-2, group, Part 2 = 75 marks)
**No brief supplied**; the mark split is quoted from the report's own cover page. Only the two criteria that a report can show were marked. Mobile client system (37) needs the running app and the demo (8) is live, so both are left out.

| Criterion | Max | Mark | Why |
|---|---|---|---|
| Problem solving and design | 15 | 13 | Problems/solutions per role tied to Part 1 research codes, 17 functional requirements, CRUD-by-role table enforced in app and Firestore rules, data model, 26-use-case diagram, wireframes for every role + tablet, MVVM with reasons, honest limitations. |
| Automated system testing | 15 | 14 | Five test levels (unit, widget, Android integration, Firestore rules on the emulator, live end-to-end on Firebase), IDs mapped to requirements, 88.4% line coverage, CI on every push, 16 real defects found and fixed (2 security-rule gaps). Small count inconsistency (108 tests vs "106 test cases"). |
| **Total (markable part)** | 30 | **27** | **90% (A+)** |

Other members' names and TP numbers appear in this report and in the DSTR code. Remove them before the repo is made public.

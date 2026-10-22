# Personal project learning guide

For every software project you create or work on, create and maintain a hidden `.project-guide.md` in its root. Explain architecture, important files, useful places to experiment, configuration and credential locations without secret values, model/runtime locations, and setup/start/stop/build/test commands and their effects. Write for a beginner and preserve the owner's notes.

Add `/.project-guide.md` to that project's `.gitignore` and verify Git ignores it. Never force-add or commit the private guide. On Windows set its Hidden file attribute. Tell the owner its exact location and how to open it. Keep a repository guide here and an application guide in `Lensly/`. Do not modify unrelated projects to add guides.

For home-desktop deployment, follow `START-HERE.md`. Keep private values, databases, runtime model weights and browser authentication state out of Git. Use the actual destination machine's paths and account; do not assume laptop paths exist.

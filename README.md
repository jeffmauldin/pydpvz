# 🌊 AllVibesDemo

> **Open-ended work, powered by agentic AI.** Pick your vibe — **Claude Code**, **Codex**, **Antigravity CLI**, or **OpenWeights** — then describe what you want and watch it get built.

This repo is a sandbox for open-ended work using agentic AI coding tools. It doesn't ship a finished app. Instead, it ships **four ready-to-run environments**, each preloaded with a different agentic AI tool. You bring the ideas; the agent writes, runs, and iterates on the code for you.

The rest of this README shows what a single prompt can turn into. Almost every example below is a prompt you can paste into any of the four tools.

---

## ✨ So… what is "agentic AI"?

You've probably used a chatbot that *answers* questions. An **agent** goes further: it can *do* things — read and write files, run commands, fix its own mistakes, and keep going until the job is done.

With a normal chatbot you ask *"how do I simulate heat flow?"* and it pastes you a tutorial to read.
With an **agentic** tool you say *"make me a heat simulation"* and it writes the files, installs what it needs, runs the program, notices the error, fixes it, and shows you the result.

That loop — **prompt → build → run → fix → show you** — is what makes these tools feel different from a chatbot. You're not writing code. You're *directing* code being written in front of you.

---

## 🧰 The four "vibes" in this repo

Each folder under `.devcontainer/` is a complete, one-click environment. Open one in [VS Code](https://code.visualstudio.com/) (with the Dev Containers extension) or [GitHub Codespaces](https://github.com/features/codespaces), and the tool installs itself automatically.

| Folder | Tool | What it is |
|---|---|---|
| `.devcontainer/claude/` | **Claude Code** | Anthropic's terminal coding agent |
| `.devcontainer/codex/` | **Codex CLI** | OpenAI's terminal coding agent |
| `.devcontainer/gemini/` | **Antigravity CLI** | Google's terminal coding agent |
| `.devcontainer/openweights/` | **OpenWeights (pi)** | Open-weight models via Ollama Cloud + web access |

The prompts in the next section are **tool-agnostic** — paste the same words into any of the four and you'll get a working program. Different tools, same one-sentence spark.

> 💡 **Tip:** Try the *same* prompt in two different tools and compare. It's interesting to see how Claude, Codex, Antigravity, and an open-weight model each interpret your idea differently.

---

## 🚀 Try this: real simulation software from a single sentence

You don't need to know physics, math, or a single line of Python. You just need to describe the *vibe* of what you want to watch happen. Below are **real, working prompts** — plain English, beginner-friendly — that produce working simulation programs in any of the four tools.

For each one you'll see:
- a **starter prompt** (copy-paste this first),
- a **level-up prompt** (a second message to send after, showing how you steer the agent),
- and **what you'll end up with**.

> The prompts are the point. The agent writes the code — you never have to.

### 🌬️ 1. Fluid dynamics — swirling smoke in a box

> **Prompt:** *"Write a Python program that simulates a 2D fluid, like swirling smoke inside a box. Animate it in real time so I can watch the flow move."*

**What you'll get:** A live, animated 2D fluid solver — dye and velocity swirling around, rendered as a color field. The classic "stable fluids" look, running in a window.

> **Level-up prompt:** *"Now let me click and drag with the mouse to push the fluid around."*

**What you'll get next:** Mouse interaction added — drag to stir the smoke, release, and watch the eddies settle. You asked one sentence; the agent updated the rendering loop, wired up the mouse, and re-ran it.

---

### 🔥 2. Heat transfer — a hot plate cooling down

> **Prompt:** *"Simulate heat spreading across a square metal plate. Make the center start hot and the edges stay cold. Animate the temperature with colors."*

**What you'll get:** A 2D heat-diffusion animation — a glowing hot spot in the middle that slowly bleeds outward into cool blue edges, looping forever. Temperature shown as a color map with a legend.

> **Level-up prompt:** *"Let me click anywhere to drop new heat sources, and add a slider for how well the metal conducts heat."*

**What you'll get next:** Click-to-add heat, a live conductivity slider, and the simulation responding instantly. Turn the slider up and the plate conducts like copper; turn it down and it acts like ceramic. You're now *experimenting* with a model you described in one sentence.

---

### 🚗 3. Traffic simulation — phantom traffic jams

> **Prompt:** *"Simulate cars driving around a circular track. Each car speeds up toward a target speed but brakes when the car ahead gets too close. Animate it and show me how traffic jams form on their own."*

**What you'll get:** Dots circling a ring road that, surprisingly, *spontaneously bunch up* into jams even though nobody caused them — the "phantom jam" effect, emerging from simple rules.

> **Level-up prompt:** *"Add a button that drops a few slow trucks onto the road and let me watch what happens to the flow."*

**What you'll get next:** A button to inject slow vehicles and a live readout of average speed. You'll see a single truck send a backwards-propagating wave through the traffic. Traffic-engineering behavior you can experiment with.

---

## 🧪 Even more ideas to try (one prompt each)

These are working programs waiting inside a single sentence. Paste any of them, then keep talking to refine:

> *"Simulate a predator–prey ecosystem with wolves and rabbits. Plot how both populations change over time and animate the animals moving around a field."*

> *"Make a 2D solar system simulator. Let me drop in planets by clicking and watch them orbit a star using real gravity."*

> *"Build a double pendulum simulator and animate it. Make it draw the trail so I can see the chaotic patterns it creates."*

> *"Simulate a flock of birds using the boids algorithm and animate them flying around obstacles."*

> *"Make a forest-fire spread simulation on a grid. Start one fire and show it spreading through trees, with wind direction I can change."*

> *"Simulate waves on a string — pluck it and watch the wave travel and reflect off the ends."*

> *"Build Conway's Game of Life with a clickable grid where I can draw starting patterns and watch them evolve."*

> *"Simulate diffusion-limited aggregation — particles randomly walking and sticking together to grow snowflake-like structures."*

Each of those is a working program, and each started as one line of English.

---

## 🪄 The pattern worth noticing

Notice the shape of every example above:

1. **Say what you want to watch happen** (one sentence).
2. **Watch the agent build and run it.**
3. **Say one more thing** — *"now let me click to add heat sources"* — and it just happens.

That second message is the useful part. You didn't edit a file. You didn't debug a stack trace. You just *described a new wish*, and the code reshaped itself. That loop — **wish → watch → wish again** — is the whole workflow. Once you're used to it, this approach can save time compared with writing everything by hand.

> 🎯 **A useful beginner skill:** learn to describe the *result* you want, not the *steps* to get there. *"Make heat spread and let me click to add sources"* tends to work better than *"initialize a 2D array and apply the finite-difference Laplacian"*. Let the agent handle the how; you own the what.

---

## 🧭 How to use this repo

1. **Pick a vibe.** Claude, Codex, Antigravity, or OpenWeights — they all do the same kind of work.
2. **Open its folder as a dev container.** In VS Code: *Dev Containers: Open Folder in Container…* → choose e.g. `.devcontainer/claude`. In Codespaces: create a codespace from the same subfolder. The tool installs itself.
3. **Start the agent** from the repo root (see the table below).
4. **Paste a prompt** from this README — or make up your own.
5. **Watch it build.** Then send a follow-up. Then another. That's it.

---

## ▶️ Running each agent

Each tool is just one command, run from the repo root inside its container. On first launch each will ask you to sign in (or you can set an API key ahead of time).

| Tool | Command | First-run sign-in |
|---|---|---|
| **Claude Code** | `claude` | Opens a browser to log in with your Anthropic account (or set `ANTHROPIC_API_KEY`). If no browser opens, it prints a URL to copy. |
| **Codex** | `codex` | Sign in with your ChatGPT account (recommended) or an OpenAI API key; opens a browser. |
| **Antigravity CLI** | `agy` | Run `agy` and follow the onboarding wizard to sign in with your Google account (free tier available). |
| **OpenWeights (pi)** | `pi` | Run `/login`, pick *Use an API key* → *Ollama Cloud*, and paste a key from [ollama.com](https://ollama.com). |

After that, just type your prompt and press Enter. The same prompts work in all four — only the sign-in step differs.

---

## 🌱 This repo is intentionally empty

There are no example programs checked in here on purpose. The point isn't to *read* someone else's finished simulations — it's to **generate your own**. Pick a prompt above, paste it into any of the four tools, and within a few minutes you'll have a simulation you started from a sentence.

Then change one word and watch the result change.

---

## 📄 License

[MIT](./LICENSE) © 2026 Wyatt Horne.
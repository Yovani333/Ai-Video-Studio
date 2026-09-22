import { Film, LoaderCircle, Sparkles } from "lucide-react";
import { FormEvent, useState } from "react";

import type { CreateProjectInput, ProjectQuality } from "../types";

const examplePrompt = "An astronaut explores an alien planet covered with glowing blue crystals.";

interface StudioFormProps {
  loading: boolean;
  onSubmit: (payload: CreateProjectInput) => Promise<void>;
}

export function StudioForm({ loading, onSubmit }: StudioFormProps) {
  const [prompt, setPrompt] = useState(examplePrompt);
  const [duration, setDuration] = useState(60);
  const [quality, setQuality] = useState<ProjectQuality>("draft");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({ prompt, duration_seconds: duration, quality });
  }

  return (
    <section className="overflow-hidden rounded-[2rem] border border-white/80 bg-white/85 shadow-soft backdrop-blur-xl">
      <div className="border-b border-black/5 px-6 py-5 sm:px-8">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-ink text-white">
            <Film size={19} />
          </span>
          <div>
            <p className="text-sm font-semibold text-ink">New production</p>
            <p className="text-xs text-zinc-500">Turn one idea into a structured scene plan.</p>
          </div>
        </div>
      </div>

      <form className="space-y-7 p-6 sm:p-8" onSubmit={handleSubmit}>
        <label className="block">
          <span className="mb-3 block text-sm font-semibold text-zinc-700">Describe your video</span>
          <textarea
            className="min-h-40 w-full resize-y rounded-2xl border border-zinc-200 bg-white p-5 text-base leading-relaxed text-ink outline-none transition placeholder:text-zinc-400 focus:border-electric focus:ring-4 focus:ring-electric/10"
            maxLength={4000}
            minLength={3}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder={examplePrompt}
            required
            value={prompt}
          />
          <span className="mt-2 block text-right text-xs text-zinc-400">{prompt.length} / 4000</span>
        </label>

        <div className="grid gap-6 sm:grid-cols-2">
          <fieldset>
            <legend className="mb-3 text-sm font-semibold text-zinc-700">Duration</legend>
            <select
              className="h-12 w-full rounded-xl border border-zinc-200 bg-white px-4 text-sm font-medium outline-none focus:border-electric focus:ring-4 focus:ring-electric/10"
              onChange={(event) => setDuration(Number(event.target.value))}
              value={duration}
            >
              <option value={30}>30 seconds</option>
              <option value={60}>60 seconds</option>
              <option value={90}>90 seconds</option>
              <option value={120}>120 seconds</option>
            </select>
          </fieldset>

          <fieldset>
            <legend className="mb-3 text-sm font-semibold text-zinc-700">Quality</legend>
            <div className="grid grid-cols-2 gap-2 rounded-xl bg-zinc-100 p-1">
              {(["draft", "final"] as ProjectQuality[]).map((option) => (
                <button
                  className={`h-10 rounded-lg text-sm font-semibold capitalize transition ${
                    quality === option
                      ? "bg-white text-ink shadow-sm"
                      : "text-zinc-500 hover:text-zinc-800"
                  }`}
                  key={option}
                  onClick={() => setQuality(option)}
                  type="button"
                >
                  {option}
                </button>
              ))}
            </div>
          </fieldset>
        </div>

        <button
          className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-ink px-6 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
          disabled={loading || prompt.trim().length < 3}
          type="submit"
        >
          {loading ? <LoaderCircle className="animate-spin" size={18} /> : <Sparkles size={18} />}
          {loading ? "Creating project..." : "Generate Video"}
        </button>
      </form>
    </section>
  );
}

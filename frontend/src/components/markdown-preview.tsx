import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

type Props = {
  children: string | null | undefined;
  className?: string;
  compact?: boolean;
};

export function MarkdownPreview({ children, className, compact = false }: Props) {
  const source = stripRawHtml(children ?? "").trim();
  if (!source) return null;
  return (
    <div className={cn("markdown-preview", compact && "markdown-preview-compact", className)}>
      <ReactMarkdown skipHtml>{source}</ReactMarkdown>
    </div>
  );
}

function stripRawHtml(value: string) {
  return value
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<[^>]+>/g, "");
}

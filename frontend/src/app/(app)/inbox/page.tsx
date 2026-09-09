import { redirect } from "next/navigation";

export default function InboxPage() {
  redirect("/tasks?view=inbox");
}

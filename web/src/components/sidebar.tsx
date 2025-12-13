"use client";

import { useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Edit3,
  MessageSquare,
  Plus,
  Search,
  Settings,
  Terminal,
  Trash2
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format, isThisMonth, isThisWeek, isToday, isYesterday } from "date-fns";
import { Session } from "@/types/session";

interface SidebarProps {
  sessions: Session[];
  currentAgentId: string | null;
  onNewSession: () => void;
  onSessionSelect: (agentId: string) => void;
  onDeleteSession: (agentId: string) => void;
  onEditTitle?: (agentId: string, title: string) => void;
  onEditSession?: (agentId: string) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

type GroupedSessions = Record<string, Session[]>;

export function Sidebar(
  {
    sessions,
    currentAgentId,
    onNewSession,
    onSessionSelect,
    onDeleteSession,
    onEditTitle,
    onEditSession,
    isCollapsed = false,
    onToggleCollapse,
  }: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    "Today": true,
    "Yesterday": true,
    "This Week": true,
    "This Month": false,
    "Older": false
  });
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  // Filter and group sessions
  const groupedSessions = useMemo(() => {
    const filtered = sessions.filter(s =>
      s.title.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const groups: GroupedSessions = {
      "Today": [],
      "Yesterday": [],
      "This Week": [],
      "This Month": [],
      "Older": []
    };

    filtered.forEach(session => {
      const date = new Date(session.lastActivityAt);
      if (isToday(date)) groups["Today"].push(session);
      else if (isYesterday(date)) groups["Yesterday"].push(session);
      else if (isThisWeek(date)) groups["This Week"].push(session);
      else if (isThisMonth(date)) groups["This Month"].push(session);
      else groups["Older"].push(session);
    });

    // Remove empty groups
    Object.keys(groups).forEach(key => {
      if (groups[key].length === 0) delete groups[key];
    });

    return groups;
  }, [sessions, searchQuery]);

  const toggleGroup = (group: string) => {
    setExpandedGroups(prev => ({
      ...prev,
      [group]: !prev[group]
    }));
  };

  const handleStartEdit = (e: React.MouseEvent, session: Session) => {
    e.stopPropagation();
    setEditingSessionId(session.agentId);
    setEditTitle(session.title);
  };

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingSessionId && onEditTitle) {
      onEditTitle(editingSessionId, editTitle);
      setEditingSessionId(null);
    }
  };

  return (
    <div
      className={cn(
        "h-full flex flex-col bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-r border-border relative transition-all duration-300 ease-in-out",
        isCollapsed ? "w-20" : "w-61.8"
      )}>
      {/* Header */}
      <div className="p-4 border-b border-border/40">
        <div className={cn(
          "flex items-center mb-4",
          isCollapsed ? "justify-center" : "gap-3"
        )}>
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <Terminal size={18}/>
          </div>
          {!isCollapsed && <h1 className="font-bold text-lg tracking-tight">AOW</h1>}
        </div>

        <button
          onClick={onNewSession}
          className={cn(
            "w-full flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md transition-all shadow-sm font-medium text-sm",
            isCollapsed ? "justify-center px-2 py-2.5" : "justify-center px-4 py-2.5"
          )}
          title={isCollapsed ? "New Agent" : undefined}
        >
          <Plus size={16}/>
          {!isCollapsed && "New Agent"}
        </button>
      </div>

      {/* Search */}
      {!isCollapsed && (
        <div className="px-4 py-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4"/>
            <input
              type="text"
              placeholder="Search chats..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-muted/50 border border-transparent focus:border-primary/20 focus:bg-background rounded-md text-sm outline-none transition-all placeholder:text-muted-foreground/70"
            />
          </div>
        </div>
      )}

      {/* Toggle Button */}
      {onToggleCollapse && (
        <button
          onClick={onToggleCollapse}
          className="absolute bottom-12 -right-3 z-10 w-6 h-6 rounded-full bg-background border border-border shadow-md hover:shadow-lg transition-all flex items-center justify-center text-muted-foreground hover:text-foreground"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <ChevronRight
            size={30}
            className={cn(
              "transition-transform duration-300",
              !isCollapsed && "rotate-180"
            )}
          />
        </button>
      )}

      {/* Session List */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-4 custom-scrollbar">
        {Object.entries(groupedSessions).map(([group, groupSessions]) => (
          <div key={group} className="space-y-1">
            <button
              onClick={() => toggleGroup(group)}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              {expandedGroups[group] ? <ChevronDown size={12}/> : <ChevronRight size={12}/>}
              {isCollapsed ? group.slice(0, 2).toUpperCase() : group}
              <span className="ml-auto text-[10px] opacity-60">{groupSessions.length}</span>
            </button>

            {expandedGroups[group] && (
              <div className="space-y-0.5">
                {groupSessions.map(session => (
                  <div
                    key={session.agentId}
                    className={cn(
                      "group relative flex items-center rounded-md cursor-pointer transition-all border border-transparent",
                      isCollapsed ? "justify-center px-2 py-2.5" : "gap-3 px-3 py-2.5",
                      currentAgentId === session.agentId
                        ? "bg-primary/10 border-primary/10 text-primary"
                        : "hover:bg-muted/60 text-foreground/80 hover:text-foreground"
                    )}
                    onClick={() => onSessionSelect(session.agentId)}
                    title={isCollapsed ? session.title : undefined}
                  >
                    <MessageSquare size={14} className={cn(
                      "shrink-0",
                      currentAgentId === session.agentId ? "text-primary" : "text-muted-foreground"
                    )}/>

                    {editingSessionId === session.agentId ? (
                      <form onSubmit={handleSaveEdit} className="flex-1 min-w-0" onClick={e => e.stopPropagation()}>
                        <input
                          autoFocus
                          type="text"
                          value={editTitle}
                          onChange={e => setEditTitle(e.target.value)}
                          onBlur={() => setEditingSessionId(null)}
                          className="w-full bg-background border border-primary/30 rounded px-1 py-0.5 text-xs outline-none"
                        />
                      </form>
                    ) : !isCollapsed ? (
                      <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                        <span className="truncate text-sm font-medium leading-none">
                          {session.title || "Untitled Chat"}
                        </span>
                        <span className="text-[10px] text-muted-foreground/70 truncate">
                          {format(session.lastActivityAt, "HH:mm")}
                        </span>
                      </div>
                    ) : null}

                    {/* Actions */}
                    {!isCollapsed && (
                      <div className={cn(
                        "absolute right-2 flex items-center gap-1 opacity-0 transition-opacity bg-background/80 backdrop-blur-sm rounded-md p-0.5 shadow-sm",
                        "group-hover:opacity-100",
                        editingSessionId === session.agentId && "hidden"
                      )}>
                        {onEditSession && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onEditSession(session.agentId);
                            }}
                            className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground transition-colors"
                            title="Settings"
                          >
                            <Settings size={12}/>
                          </button>
                        )}
                        {onEditTitle && (
                          <button
                            onClick={(e) => handleStartEdit(e, session)}
                            className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground transition-colors"
                            title="Rename"
                          >
                            <Edit3 size={12}/>
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(session.agentId);
                          }}
                          className="p-1.5 hover:bg-destructive/10 rounded-md text-muted-foreground hover:text-destructive transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={12}/>
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {sessions.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <div className="w-12 h-12 rounded-full bg-muted/50 flex items-center justify-center mb-3">
              <MessageSquare size={20} className="text-muted-foreground/50"/>
            </div>
            <p className="text-sm text-muted-foreground">No conversations yet</p>
            <p className="text-xs text-muted-foreground/50 mt-1">Start a new chat to begin</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border/40 bg-muted/20">
        <button
          className={cn(
            "w-full flex items-center rounded-md hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors text-sm",
            isCollapsed ? "justify-center px-2 py-2" : "gap-3 px-3 py-2"
          )}
          title={isCollapsed ? "Settings" : undefined}
        >
          <Settings size={16}/>
          {!isCollapsed && <span>Settings</span>}
        </button>
      </div>
    </div>
  );
}

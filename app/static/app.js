const STACK_OPTIONS = {
  language: ["Auto", "Python", "JavaScript", "TypeScript", "Java"],
  frontend: ["Auto", "None", "HTML/CSS/JavaScript", "React", "Next.js", "Vue"],
  backend: ["Auto", "None", "FastAPI", "Flask", "Express", "NestJS", "Spring Boot"],
  database: ["Auto", "None", "SQLite", "PostgreSQL", "MySQL", "MongoDB"],
  aiTools: ["Auto", "None", "Ollama", "OpenAI API", "LangChain"],
  deployment: ["Auto", "None", "Render", "Railway", "Vercel", "Docker"],
};

const ideaInput = document.getElementById("ideaInput");
const suggestButton = document.getElementById("suggestButton");
const skipSuggestButton = document.getElementById("skipSuggestButton");
const askQuestionsButton = document.getElementById("askQuestionsButton");
const continueButton = document.getElementById("continueButton");
const skipQuestionsButton = document.getElementById("skipQuestionsButton");
const generateProjectButton = document.getElementById("generateProjectButton");
const regenerateButton = document.getElementById("regenerateButton");
const confirmButton = document.getElementById("confirmButton");
const clearButton = document.getElementById("clearButton");
const statusMessage = document.getElementById("statusMessage");
const generationModeSelect = document.getElementById("generationModeSelect");
const agentActivityPanel = document.getElementById("agentActivityPanel");
const agentActivityList = document.getElementById("agentActivityList");

const agentSection = document.getElementById("agentSection");
const advancedStackSection = document.getElementById("advancedStackSection");
const previewSection = document.getElementById("previewSection");
const downloadSection = document.getElementById("downloadSection");

const agentUnderstandingText = document.getElementById("agentUnderstandingText");
const agentAssumptionsList = document.getElementById("agentAssumptionsList");
const agentSuggestedStackList = document.getElementById("agentSuggestedStackList");
const questionCards = document.getElementById("questionCards");
const finalizeCard = document.getElementById("finalizeCard");
const finalizeSummaryText = document.getElementById("finalizeSummaryText");
const finalSelectedStackList = document.getElementById("finalSelectedStackList");
const finalRequirementsText = document.getElementById("finalRequirementsText");

const projectNameHeading = document.getElementById("projectNameHeading");
const detectedChoicesList = document.getElementById("detectedChoicesList");
const stackChips = document.getElementById("stackChips");
const selectedStackList = document.getElementById("selectedStackList");
const toolRecommendationList = document.getElementById("toolRecommendationList");
const stackAnalysisList = document.getElementById("stackAnalysisList");
const migrationSummaryList = document.getElementById("migrationSummaryList");
const chosenStackList = document.getElementById("chosenStackList");
const assumptionsList = document.getElementById("assumptionsList");
const summaryText = document.getElementById("summaryText");
const problemStatementText = document.getElementById("problemStatementText");
const architectureList = document.getElementById("architectureList");
const packageRequirementsList = document.getElementById("packageRequirementsList");
const installCommandsList = document.getElementById("installCommandsList");
const runCommandsList = document.getElementById("runCommandsList");
const envVariablesList = document.getElementById("envVariablesList");
const requiredInputsBody = document.getElementById("requiredInputsBody");
const mainFileText = document.getElementById("mainFileText");
const runMethodText = document.getElementById("runMethodText");
const localUrlText = document.getElementById("localUrlText");
const runtimeInputsSummaryText = document.getElementById("runtimeInputsSummaryText");
const modulesList = document.getElementById("modulesList");
const fileTreeBlock = document.getElementById("fileTreeBlock");
const filesList = document.getElementById("filesList");
const downloadText = document.getElementById("downloadText");
const downloadLink = document.getElementById("downloadLink");
const chatPanel = document.getElementById("chatPanel");
const chatToggleButton = document.getElementById("chatToggleButton");
const chatCloseButton = document.getElementById("chatCloseButton");
const chatMessagesElement = document.getElementById("chatMessages");
const chatActionBar = document.getElementById("chatActionBar");
const chatInput = document.getElementById("chatInput");
const chatSendButton = document.getElementById("chatSendButton");
const chatModeBadge = document.getElementById("chatModeBadge");

const stackSelects = {
  language: document.getElementById("languageSelect"),
  frontend: document.getElementById("frontendSelect"),
  backend: document.getElementById("backendSelect"),
  database: document.getElementById("databaseSelect"),
  aiTools: document.getElementById("aiToolsSelect"),
  deployment: document.getElementById("deploymentSelect"),
};

let baseIdea = "";
let agentAnalysis = null;
let agentAnswers = {};
let finalRequirements = "";
let currentPreview = null;
let selectedStack = getDefaultStackState();
let suggestedStack = getDefaultStackState();
let currentStackSelection = createCurrentStackSelection(getDefaultStackState(), {
  source: "initial_default",
});
let isApplyingStackToControls = false;
let currentQuestionIndex = 0;
let currentQuestionDraft = "";
let showingSuggestion = false;
let chatMessages = [];
let chatDraftIdea = "";
let chatFinalRequirements = "";
let chatPendingCorrections = [];
let chatRequestedFiles = [];
let chatFilesToRemove = [];
let chatUpdatedStack = null;
let chatMode = "idea_discussion";
let chatLinkedPreviewId = "";
let isAgentRunning = false;
let pendingAgentUpdate = null;
let isApplyingPendingAgentUpdate = false;
let llmModeUsed = "free_rule_based";
let lastChatAction = null;
let agentActivityState = {
  understood: "pending",
  analyzed: "pending",
  migrated: "pending",
  stack: "pending",
  planned: "pending",
  generated: "pending",
  tools: "pending",
  validated: "pending",
  repaired: "pending",
  ready: "pending",
};

initializeStackSelectors();
resetAgentActivity();
refreshUiState();

suggestButton.addEventListener("click", handleGenerateAfterQuestions);
skipSuggestButton.addEventListener("click", handleSkipToAgentSuggestion);
askQuestionsButton.addEventListener("click", handleAskQuestions);
continueButton.addEventListener("click", handleContinueAgent);
skipQuestionsButton.addEventListener("click", handleSkipQuestions);
generateProjectButton.addEventListener("click", handleGenerateProject);
regenerateButton.addEventListener("click", handleRegenerate);
confirmButton.addEventListener("click", handleConfirmZip);
clearButton.addEventListener("click", resetAll);
chatToggleButton.addEventListener("click", toggleChatPanel);
chatCloseButton.addEventListener("click", closeChatPanel);
chatSendButton.addEventListener("click", sendChatMessage);
chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    void sendChatMessage();
  }
});

Object.entries(stackSelects).forEach(([key, select]) => {
  select.addEventListener("change", () => handleStackChange(key));
});

function initializeStackSelectors() {
  Object.entries(stackSelects).forEach(([key, select]) => {
    STACK_OPTIONS[key].forEach((option) => {
      const optionElement = document.createElement("option");
      optionElement.value = option;
      optionElement.textContent = option;
      select.appendChild(optionElement);
    });
  });
  applySelectedStackToControls(getDefaultStackState());
}

function getDefaultStackState() {
  return {
    language: "Auto",
    frontend: "Auto",
    backend: "Auto",
    database: "Auto",
    aiTools: "Auto",
    deployment: "Auto",
  };
}

function getQuestionList() {
  return Array.isArray(agentAnalysis?.questions) ? agentAnalysis.questions : [];
}

function getCurrentQuestion() {
  const questions = getQuestionList();
  return questions[currentQuestionIndex] || null;
}

function getStoredAnswer(questionId) {
  return typeof agentAnswers[questionId] === "string" ? agentAnswers[questionId] : "";
}

function setQuestionDraft(value) {
  currentQuestionDraft = String(value || "");
}

function resetQuestionFlow() {
  currentQuestionIndex = 0;
  currentQuestionDraft = "";
  showingSuggestion = false;
}

function collectSelectedStack() {
  return {
    language: stackSelects.language.value,
    frontend: stackSelects.frontend.value,
    backend: stackSelects.backend.value,
    database: stackSelects.database.value,
    aiTools: stackSelects.aiTools.value,
    deployment: stackSelects.deployment.value,
  };
}

function createCurrentStackSelection(stack, metadata = {}) {
  const safeStack = stack || getDefaultStackState();
  return {
    language: safeStack.language || "Auto",
    frontend: safeStack.frontend || "Auto",
    backend: safeStack.backend || "Auto",
    database: safeStack.database || "Auto",
    aiTools: safeStack.aiTools || "Auto",
    deployment: safeStack.deployment || "Auto",
    source: metadata.source || safeStack.source || "advanced_settings_stack",
    runtimeTools: metadata.runtimeTools || safeStack.runtimeTools || [],
    packageManager: metadata.packageManager || safeStack.packageManager || "",
    lastModifiedField: metadata.lastModifiedField || safeStack.lastModifiedField || "",
    lastModifiedAt: metadata.lastModifiedAt || safeStack.lastModifiedAt || null,
    isUserConfirmedStack: Boolean(metadata.isUserConfirmedStack ?? safeStack.isUserConfirmedStack ?? false),
    isDirty: Boolean(metadata.isDirty ?? safeStack.isDirty ?? false),
  };
}

function getStackFields(stack) {
  const source = stack || getDefaultStackState();
  return {
    language: source.language || "Auto",
    frontend: source.frontend || "Auto",
    backend: source.backend || "Auto",
    database: source.database || "Auto",
    aiTools: source.aiTools || "Auto",
    deployment: source.deployment || "Auto",
  };
}

function getCurrentStackSelection() {
  const latestStack = collectSelectedStack();
  currentStackSelection = createCurrentStackSelection(latestStack, {
    ...currentStackSelection,
    source: currentStackSelection.source || "advanced_settings_stack",
  });
  selectedStack = getStackFields(currentStackSelection);
  return currentStackSelection;
}

function setCurrentStackSelectionFromStack(stack, metadata = {}) {
  currentStackSelection = createCurrentStackSelection(stack, metadata);
  selectedStack = getStackFields(currentStackSelection);
}

function applySelectedStackToControls(stack, metadata = {}) {
  const safeStack = stack || getDefaultStackState();
  isApplyingStackToControls = true;
  Object.entries(stackSelects).forEach(([key, select]) => {
    select.value = safeStack[key] || "Auto";
  });
  isApplyingStackToControls = false;
  setCurrentStackSelectionFromStack(collectSelectedStack(), {
    source: metadata.source || safeStack.source || currentStackSelection.source || "advanced_settings_stack",
    runtimeTools: safeStack.runtimeTools || metadata.runtimeTools || [],
    packageManager: safeStack.packageManager || metadata.packageManager || "",
    lastModifiedField: metadata.lastModifiedField || safeStack.lastModifiedField || currentStackSelection.lastModifiedField || "",
    lastModifiedAt: metadata.lastModifiedAt || safeStack.lastModifiedAt || currentStackSelection.lastModifiedAt || null,
    isUserConfirmedStack: Boolean(metadata.isUserConfirmedStack ?? safeStack.isUserConfirmedStack ?? currentStackSelection.isUserConfirmedStack ?? false),
    isDirty: Boolean(metadata.isDirty ?? safeStack.isDirty ?? currentStackSelection.isDirty ?? false),
  });
}

function mergeManualStackWithSuggestion(manualStack, suggestedStack) {
  const defaults = getDefaultStackState();
  const suggestion = suggestedStack || defaults;
  const manual = manualStack || defaults;
  return Object.fromEntries(
    Object.keys(defaults).map((key) => {
      const manualValue = manual[key] || "Auto";
      return [key, manualValue !== "Auto" ? manualValue : suggestion[key] || "Auto"];
    }),
  );
}

function handleStackChange(editedField) {
  if (isApplyingStackToControls) {
    return;
  }
  setCurrentStackSelectionFromStack(collectSelectedStack(), {
    ...currentStackSelection,
    source: "user_modified_suggestion",
    isUserConfirmedStack: true,
    isDirty: true,
    lastModifiedField: editedField,
    lastModifiedAt: Date.now(),
  });
  refreshUiState();
}

function setStatus(message, type) {
  statusMessage.hidden = false;
  statusMessage.className = `status-message ${type}`;
  statusMessage.textContent = message;
}

function clearStatus() {
  statusMessage.hidden = true;
  statusMessage.className = "status-message";
  statusMessage.textContent = "";
}

function resetAgentActivity() {
  agentActivityState = {
    understood: "pending",
    analyzed: "pending",
    migrated: "pending",
    stack: "pending",
    planned: "pending",
    generated: "pending",
    tools: "pending",
    validated: "pending",
    repaired: "pending",
    ready: "pending",
  };
  renderAgentActivity();
}

function setAgentActivity(nextState) {
  agentActivityState = {
    ...agentActivityState,
    ...nextState,
  };
  renderAgentActivity();
}

function renderAgentActivity() {
  if (!agentActivityPanel || !agentActivityList) {
    return;
  }

  const hasVisibleState = Object.values(agentActivityState).some((value) => value !== "pending");
  agentActivityPanel.hidden = !hasVisibleState;

  Array.from(agentActivityList.querySelectorAll("li")).forEach((item) => {
    const step = item.dataset.step;
    const state = agentActivityState[step] || "pending";
    item.dataset.state = state;
  });
}

function setBusy(isBusy, message = "Working...") {
  isAgentRunning = isBusy;
  suggestButton.disabled = isBusy;
  skipSuggestButton.disabled = isBusy;
  askQuestionsButton.disabled = isBusy;
  continueButton.disabled = isBusy || !agentAnalysis;
  skipQuestionsButton.disabled = isBusy || !agentAnalysis;
  generateProjectButton.disabled = isBusy || !finalRequirements;
  regenerateButton.disabled = isBusy || !currentPreview;
  confirmButton.disabled = isBusy || !currentPreview;
  clearButton.disabled = isBusy && !baseIdea && !currentPreview && !agentAnalysis;
  generationModeSelect.disabled = isBusy;
  Object.values(stackSelects).forEach((select) => {
    select.disabled = isBusy;
  });
  if (isBusy) {
    setStatus(message, "loading");
  }
}

function refreshUiState() {
  continueButton.disabled = !agentAnalysis;
  skipQuestionsButton.disabled = !agentAnalysis;
  generateProjectButton.disabled = !finalRequirements;
  regenerateButton.disabled = !currentPreview;
  confirmButton.disabled = !currentPreview;
  clearButton.disabled = !baseIdea && !currentPreview && !agentAnalysis;
  skipSuggestButton.disabled = false;
  Object.values(stackSelects).forEach((select) => {
    select.disabled = false;
  });

  const questions = getQuestionList();
  const hasQuestionFlow = !!agentAnalysis && questions.length > 0 && !finalRequirements;
  if (hasQuestionFlow) {
    continueButton.disabled = showingSuggestion;
    continueButton.textContent = currentQuestionIndex >= questions.length - 1 ? "Finish Questions" : "Next";
  } else if (!!agentAnalysis && !finalRequirements) {
    continueButton.textContent = "Continue";
  } else {
    continueButton.textContent = "Next";
  }
}

async function handleGenerateAfterQuestions() {
  if (finalRequirements) {
    await handleGenerateProject();
    return;
  }
  await handleAskQuestions();
}

async function handleGenerateImmediately() {
  const idea = ideaInput.value.trim();
  if (!idea) {
    setStatus("Please enter a project idea before generating the starter.", "error");
    return;
  }

  baseIdea = idea;
  agentAnalysis = null;
  agentAnswers = {};
  finalRequirements = "";
  currentPreview = null;
  resetQuestionFlow();
  resetAgentActivity();
  agentSection.hidden = true;
  previewSection.hidden = true;
  downloadSection.hidden = true;
  finalizeCard.hidden = true;
  advancedStackSection.hidden = true;
  setAgentActivity({
    understood: "done",
    analyzed: "done",
    migrated: "done",
    stack: "done",
    planned: "done",
    generated: "current",
  });
  setBusy(true, "Generating runnable starter project...");

  try {
    const stackSelection = getCurrentStackSelection();
    const payload = await requestPreview({
      idea,
      selectedStack: stackSelection,
      finalRequirements: "",
    });
    currentPreview = payload;
    applySelectedStackToControls(payload.selectedStack || stackSelection, {
      source: payload.stackSelectionSource || stackSelection.source,
      isUserConfirmedStack: stackSelection.isUserConfirmedStack,
      isDirty: stackSelection.isDirty,
    });
    renderPreview(payload);
    setAgentActivity({
      generated: "done",
      tools: "done",
      validated: "done",
      repaired: "done",
      ready: "done",
    });
    setStatus("Project preview is ready. You can regenerate with a different stack or create the ZIP.", "success");
  } catch (error) {
    currentPreview = null;
    previewSection.hidden = true;
    setAgentActivity({
      generated: "done",
      tools: "done",
      validated: "done",
      repaired: "done",
      ready: "pending",
    });
    setStatus(error.message || "Could not generate the runnable starter.", "error");
  } finally {
    clearBusyState();
  }
}

async function handleAskQuestions() {
  const idea = ideaInput.value.trim();
  if (!idea) {
    setStatus("Please enter a project idea before starting the agent questions.", "error");
    return;
  }

  baseIdea = idea;
  currentPreview = null;
  finalRequirements = "";
  agentAnswers = {};
  resetQuestionFlow();
  resetAgentActivity();
  previewSection.hidden = true;
  downloadSection.hidden = true;
  finalizeCard.hidden = true;
  setAgentActivity({
    understood: "current",
  });
  setBusy(true, "Analyzing your idea and preparing questions...");

  try {
    const manualStack = getStackFields(getCurrentStackSelection());
    const payload = await requestAgentAnalysis(idea);
    agentAnalysis = payload;
    suggestedStack = payload.suggestedStack || getDefaultStackState();
    const mergedStack = mergeManualStackWithSuggestion(manualStack, suggestedStack);
    applySelectedStackToControls(mergedStack, {
      source: "original_suggested_stack",
      isUserConfirmedStack: false,
      isDirty: false,
    });
    renderAgentAnalysis(payload);
    agentSection.hidden = false;
    advancedStackSection.hidden = true;
    setAgentActivity({
      understood: "done",
      analyzed: "done",
      migrated: "done",
      stack: "done",
      planned: "done",
    });
    setStatus("The agent reviewed your idea. Answer the questions one by one, or skip and use suggested defaults.", "success");
  } catch (error) {
    agentAnalysis = null;
    agentSection.hidden = true;
    setStatus(error.message || "Could not start the agent questions.", "error");
  } finally {
    clearBusyState();
  }
}

async function handleSkipToAgentSuggestion() {
  const idea = ideaInput.value.trim();
  if (!idea) {
    setStatus("Please enter a project idea before letting the agent suggest a stack.", "error");
    return;
  }

  baseIdea = idea;
  currentPreview = null;
  finalRequirements = "";
  agentAnswers = {};
  resetQuestionFlow();
  resetAgentActivity();
  previewSection.hidden = true;
  downloadSection.hidden = true;
  finalizeCard.hidden = true;
  setAgentActivity({
    understood: "current",
  });
  setBusy(true, "Agent is suggesting a stack and preparing questions...");

  try {
    const payload = await requestAgentAnalysis(idea);
    agentAnalysis = payload;
    suggestedStack = payload.suggestedStack || getDefaultStackState();
    applySelectedStackToControls(suggestedStack, {
      source: "original_suggested_stack",
      isUserConfirmedStack: false,
      isDirty: false,
    });
    renderAgentAnalysis(payload);
    agentSection.hidden = false;
    advancedStackSection.hidden = true;
    setAgentActivity({
      understood: "done",
      analyzed: "done",
      migrated: "done",
      stack: "done",
      planned: "done",
    });
    finalRequirements = "";
    setStatus("Agent suggested a tech stack. Answer the questions one by one before generation.", "success");
  } catch (error) {
    agentAnalysis = null;
    agentSection.hidden = true;
    setStatus(error.message || "Could not prepare questions from the agent-suggested stack.", "error");
  } finally {
    clearBusyState();
  }
}

async function handleContinueAgent() {
  if (!baseIdea || !agentAnalysis) {
    setStatus("Start the agent before continuing.", "error");
    return;
  }

  const question = getCurrentQuestion();
  if (!question) {
    await finalizeConversationOnly();
    return;
  }

  const typedAnswer = currentQuestionDraft.trim();
  if (!typedAnswer) {
    showingSuggestion = true;
    renderQuestionFlow();
    setStatus("No answer was entered. Review the suggested default or edit your answer.", "info");
    return;
  }

  storeQuestionAnswer(question.id, typedAnswer);
  moveToNextQuestion();
}

async function handleSkipQuestions() {
  if (!baseIdea || !agentAnalysis) {
    setStatus("Start the agent before skipping questions.", "error");
    return;
  }

  downloadSection.hidden = true;
  setBusy(true, "Letting the agent answer the remaining questions...");

  try {
    await finalizeAgentConversation({ fillDefaults: true });
    setStatus("Agent filled the answers. Generate the project when you are ready.", "success");
  } catch (error) {
    currentPreview = null;
    previewSection.hidden = true;
    setStatus(error.message || "Could not finalize the agent-suggested answers.", "error");
  } finally {
    clearBusyState();
  }
}

async function handleGenerateProject() {
  if (!baseIdea || !finalRequirements) {
    setStatus("Finalize the agent conversation before generating the project.", "error");
    return;
  }

  downloadSection.hidden = true;
  setBusy(true, "Generating project preview...");

  try {
    await generatePreviewFromCurrentState(
      "Preview ready. Review the generated project, regenerate if needed, then confirm to create the ZIP.",
    );
  } catch (error) {
    currentPreview = null;
    previewSection.hidden = true;
    setStatus(error.message || "Could not generate the project preview.", "error");
  } finally {
    clearBusyState();
  }
}

async function handleRegenerate() {
  if (!baseIdea || !currentPreview) {
    setStatus("Generate a preview before regenerating with the selected stack.", "error");
    return;
  }

  downloadSection.hidden = true;
  setBusy(true, "Generating project preview...");

  try {
    await generatePreviewFromCurrentState(
      "Preview regenerated with the latest requirements and selected stack.",
    );
  } catch (error) {
    setStatus(error.message || "Could not regenerate the preview.", "error");
  } finally {
    clearBusyState();
  }
}

async function handleConfirmZip() {
  if (!currentPreview) {
    setStatus("Generate a preview before creating a ZIP.", "error");
    return;
  }

  setBusy(true, "Creating ZIP from the latest accepted preview...");
  setAgentActivity({
    validated: "current",
    repaired: "current",
    ready: "current",
  });

  try {
    const stackSelection = getCurrentStackSelection();
    if (stackSelection.isDirty) {
      currentPreview = {
        ...currentPreview,
        selectedStack: getStackFields(stackSelection),
        stackSelectionSource: stackSelection.source,
        isUserConfirmedStack: stackSelection.isUserConfirmedStack,
      };
    }
    currentPreview = {
      ...currentPreview,
      customFiles: mergeRequestedFiles(currentPreview.customFiles || [], chatRequestedFiles),
      requestedFiles: mergeRequestedFiles(currentPreview.requestedFiles || [], chatRequestedFiles),
      filesToRemove: mergeFilesToRemove(currentPreview.filesToRemove || [], chatFilesToRemove),
      chatPendingCorrections,
    };
    const response = await fetch("/api/zip", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        preview: currentPreview,
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not create the ZIP.");
    }

    downloadLink.href = payload.downloadUrl;
    downloadLink.download = payload.filename;
    downloadText.textContent = `Your generated project ZIP is ready: ${payload.filename}`;
    downloadSection.hidden = false;
    setAgentActivity({
      validated: "done",
      repaired: "done",
      ready: "done",
    });
    setStatus("ZIP created successfully. You can download it now.", "success");
  } catch (error) {
    setStatus(error.message || "Could not create the ZIP.", "error");
  } finally {
    clearBusyState();
  }
}

// Chat popup functionality
function openChatPanel() {
  chatPanel.classList.remove("closed");
  chatPanel.classList.add("open", "is-open");
  chatToggleButton.classList.remove("closed");
  chatToggleButton.classList.add("open");
  chatToggleButton.setAttribute("aria-expanded", "true");
  renderChatMessages();
  chatInput.focus();
}

function closeChatPanel() {
  chatPanel.classList.remove("open", "is-open");
  chatPanel.classList.add("closed");
  chatToggleButton.classList.remove("open");
  chatToggleButton.classList.add("closed");
  chatToggleButton.setAttribute("aria-expanded", "false");
}

function toggleChatPanel() {
  if (chatPanel.classList.contains("is-open")) {
    closeChatPanel();
  } else {
    openChatPanel();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  closeChatPanel();
  renderChatMessages();

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeChatPanel();
    }
  });
});

async function sendChatMessage() {
  await handleChatSend();
}

async function handleChatSend() {
  const message = chatInput.value.trim();
  if (!message) {
    return;
  }
  chatInput.value = "";
  appendChatMessage("user", message);
  chatMode = resolveChatMode();

  try {
    chatSendButton.disabled = true;
    const response = await requestChat(message);
    lastChatAction = response;
    llmModeUsed = response.llmModeUsed || "free_rule_based";
    chatModeBadge.textContent = llmModeUsed === "ollama" ? "Ollama Mode" : "Free Rule Mode";
    appendChatMessage("assistant", response.reply || "I understood that.");
    renderChatActions(response);
    if (response.action === "update_requirements" && !response.needsConfirmation) {
      chatDraftIdea = response.updatedIdea || message;
      chatFinalRequirements = response.updatedRequirements || response.updatedIdea || message;
    }
  } catch (error) {
    appendChatMessage("assistant", error.message || "Chat is still available in Free Rule Mode, but this request failed.");
  } finally {
    chatSendButton.disabled = false;
  }
}

async function requestChat(message) {
  const response = await fetch("/api/agent/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      conversation: chatMessages.slice(-10),
      currentIdea: baseIdea || ideaInput.value.trim(),
      currentPreview: currentPreview || {},
      selectedStack: getCurrentStackSelection(),
      agentState: isAgentRunning ? "running" : currentPreview ? "preview_ready" : "idle",
      pendingCorrections: chatPendingCorrections,
      llmMode: "auto",
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Could not send chat message.");
  }
  return payload;
}

function appendChatMessage(role, content) {
  chatMessages.push({ role, content });
  renderChatMessage();
}

function renderChatMessage() {
  renderChatMessages();
}

function renderChatMessages() {
  chatMessagesElement.replaceChildren();
  if (!chatMessages.length) {
    const empty = document.createElement("p");
    empty.className = "chat-empty";
    empty.textContent = "Ask me to improve an idea, add files, change stack, or regenerate your preview.";
    chatMessagesElement.appendChild(empty);
    return;
  }
  chatMessages.forEach((message) => {
    const bubble = document.createElement("article");
    bubble.className = `chat-message ${message.role === "user" ? "user" : "assistant"}`;
    bubble.textContent = message.content;
    chatMessagesElement.appendChild(bubble);
  });
  chatMessagesElement.scrollTop = chatMessagesElement.scrollHeight;
}

function renderChatActions(action) {
  chatActionBar.replaceChildren();
  chatActionBar.hidden = false;

  if (!action || action.action === "none") {
    chatActionBar.hidden = true;
    return;
  }

  if (action.updatedIdea || action.updatedRequirements) {
    addChatActionButton("Use as Project Description", () => applyChatIdea(action));
  }
  if (action.needsConfirmation) {
    const confirmLabel = action.action === "change_stack"
      ? "Change Stack"
      : action.action === "generate_project"
        ? "Generate Project"
      : action.action === "remove_files" || action.action === "remove_feature"
        ? "Apply Corrections"
      : action.action === "add_files"
        ? "Add To Current Project"
        : "Apply Corrections";
    addChatActionButton(confirmLabel, () => applyChatAction(action));
    addChatActionButton("Cancel", cancelChatAction, "ghost-button");
  }
  if (!action.needsConfirmation && (action.shouldGenerate || action.action === "generate_project")) {
    addChatActionButton("Generate Project", () => applyChatGenerate(action));
  }
  if (action.shouldRegenerate || action.action === "regenerate_project") {
    addChatActionButton("Regenerate Project", () => regenerateFromChat(action));
  }
  if (!chatActionBar.children.length) {
    chatActionBar.hidden = true;
  }
}

function addChatActionButton(label, handler, className = "secondary-button") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", () => {
    void handler();
  });
  chatActionBar.appendChild(button);
}

function useChatAsProjectDescription(action) {
  applyChatIdea(action);
}

function applyChatIdea(action) {
  const nextIdea = action.updatedIdea || action.updatedRequirements || "";
  const nextRequirements = action.updatedRequirements || nextIdea;
  if (nextIdea) {
    ideaInput.value = nextIdea;
    baseIdea = nextIdea;
  }
  if (nextRequirements) {
    finalRequirements = nextRequirements;
    finalRequirementsText.textContent = nextRequirements;
    finalizeCard.hidden = false;
  }
  chatDraftIdea = nextIdea;
  chatFinalRequirements = nextRequirements;
  setStatus("Chat description copied into the project idea. Generate when ready.", "success");
  refreshUiState();
}

async function applyChatAction(action) {
  if (!action) {
    return;
  }
  if (action.shouldPauseAgent && isAgentRunning) {
    pendingAgentUpdate = action;
    chatPendingCorrections.push(action);
    chatActionBar.hidden = true;
    setStatus("Chat correction captured. I will apply it after the current preview is ready.", "success");
    return;
  }
  if (action.action === "change_stack" && action.updatedStack) {
    await applyChatStack(action);
    return;
  }
  if (action.action === "generate_project" || action.shouldGenerate) {
    await applyChatGenerate(action);
    return;
  }
  if (action.action === "remove_files" || action.action === "remove_feature" || action.filesToRemove?.length) {
    await applyChatRemoveFiles(action);
    return;
  }
  if (action.action === "add_files" || action.action === "add_feature" || action.action === "update_required_inputs" || action.shouldRegenerate || action.updatedRequirements || action.requestedFiles?.length) {
    await applyChatCorrections(action);
    return;
  }
  mergeChatActionState(action);
  setStatus("Chat corrections are staged. Generate or regenerate to apply them.", "success");
  refreshUiState();
}

async function applyChatCorrections(action) {
  mergeChatActionState(action);
  chatActionBar.hidden = true;
  if (currentPreview) {
    await regenerateFromChat(action, { alreadyMerged: true });
    return;
  }
  await generateFromChat(action, { alreadyMerged: true });
}

async function applyChatRemoveFiles(action) {
  mergeChatActionState(action);
  chatActionBar.hidden = true;
  if (currentPreview) {
    currentPreview = {
      ...currentPreview,
      files: removePreviewFiles(currentPreview.files || [], chatFilesToRemove),
      customFiles: removeManifestFiles(currentPreview.customFiles || [], chatFilesToRemove),
      requestedFiles: removeManifestFiles(currentPreview.requestedFiles || [], chatFilesToRemove),
      filesToRemove: mergeFilesToRemove(currentPreview.filesToRemove || [], chatFilesToRemove),
    };
  }
  await regenerateFromChat(action, { alreadyMerged: true });
}

async function applyChatGenerate(action) {
  applyChatIdea(action);
  await generateFromChat(action);
}

async function applyChatStack(action) {
  mergeChatActionState(action);
  applySelectedStackToControls(action.updatedStack, {
    source: "chatbot_stack_change",
    isUserConfirmedStack: true,
    isDirty: true,
    lastModifiedField: action.updatedStack.lastModifiedField || "backend",
    lastModifiedAt: Date.now(),
  });
  chatActionBar.hidden = true;
  if (action.shouldRegenerate && currentPreview) {
    await regenerateFromChat(action, { alreadyMerged: true });
    return;
  }
  setStatus("Chat stack change is staged. Generate or regenerate to apply it.", "success");
  refreshUiState();
}

function mergeChatActionState(action) {
  const nextIdea = action.updatedIdea || baseIdea || ideaInput.value.trim();
  const nextRequirements = action.updatedRequirements || finalRequirements || nextIdea;
  if (nextIdea) {
    baseIdea = nextIdea;
    ideaInput.value = nextIdea;
  }
  if (nextRequirements) {
    finalRequirements = nextRequirements;
  }
  chatFinalRequirements = nextRequirements;
  chatRequestedFiles = mergeRequestedFiles(chatRequestedFiles, action.requestedFiles || []);
  chatFilesToRemove = mergeFilesToRemove(chatFilesToRemove, action.filesToRemove || []);
  chatPendingCorrections.push(action);
}

function mergeRequestedFiles(existing, incoming) {
  const merged = new Map();
  [...(existing || []), ...(incoming || [])].forEach((item) => {
    if (item && item.path) {
      merged.set(item.path, item);
    }
  });
  return [...merged.values()];
}

function mergeFilesToRemove(existing, incoming) {
  const merged = new Map();
  [...(existing || []), ...(incoming || [])].forEach((item) => {
    const path = typeof item === "string" ? item : item?.path;
    if (path) {
      merged.set(path, typeof item === "string" ? { path } : item);
    }
  });
  return [...merged.values()];
}

function removePreviewFiles(files, removals) {
  const removed = new Set((removals || []).map((item) => typeof item === "string" ? item : item?.path).filter(Boolean));
  return (files || []).filter((item) => !removed.has(item.path));
}

function removeManifestFiles(files, removals) {
  const removed = new Set((removals || []).map((item) => typeof item === "string" ? item : item?.path).filter(Boolean));
  return (files || []).filter((item) => !removed.has(item.path));
}

async function generateFromChat(action, options = {}) {
  if (!options.alreadyMerged) {
    mergeChatActionState(action);
  }
  if (!baseIdea) {
    setStatus("Chat did not provide a project idea to generate.", "error");
    return;
  }
  downloadSection.hidden = true;
  setBusy(true, "Generating project from chat...");
  try {
    const payload = await requestPreview({
      idea: baseIdea,
      selectedStack: getCurrentStackSelection(),
      finalRequirements: chatFinalRequirements || finalRequirements || baseIdea,
      customFiles: chatRequestedFiles,
      requestedFiles: chatRequestedFiles,
      filesToRemove: chatFilesToRemove,
      chatPendingCorrections,
    });
    currentPreview = payload;
    renderPreview(payload);
    setStatus("Project generated from chat description.", "success");
  } catch (error) {
    setStatus(error.message || "Could not generate from chat.", "error");
  } finally {
    clearBusyState();
  }
}

async function regenerateFromChat(action, options = {}) {
  if (!options.alreadyMerged) {
    mergeChatActionState(action);
  }
  if (!baseIdea && currentPreview) {
    baseIdea = currentPreview.problemStatement || currentPreview.summary || currentPreview.projectName || "";
  }
  downloadSection.hidden = true;
  setBusy(true, "Regenerating project with chat corrections...");
  try {
    await generatePreviewFromCurrentState("Preview regenerated with chat corrections.");
    pendingAgentUpdate = null;
  } catch (error) {
    setStatus(error.message || "Could not regenerate with chat corrections.", "error");
  } finally {
    clearBusyState();
  }
}

function cancelChatAction() {
  lastChatAction = null;
  chatActionBar.hidden = true;
  appendChatMessage("assistant", "Canceled. I did not change the project.");
}

function resolveChatMode() {
  if (isAgentRunning) {
    return "agent_interruption";
  }
  if (currentPreview) {
    return "preview_modification";
  }
  return "idea_discussion";
}

async function requestAgentAnalysis(idea) {
  const response = await fetch("/api/agent/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ idea }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Could not analyze the idea.");
  }
  return payload;
}

async function requestAgentFinalize(body) {
  const response = await fetch("/api/agent/finalize", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Could not finalize the requirements.");
  }
  return payload;
}

async function requestPreview(body) {
  const stackSelection = body.selectedStack || getCurrentStackSelection();
  const customFiles = mergeRequestedFiles(chatRequestedFiles, body.customFiles || []);
  const filesToRemove = mergeFilesToRemove(chatFilesToRemove, body.filesToRemove || []);
  const response = await fetch("/api/suggest", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      generationMode: generationModeSelect.value || "fast",
      ...body,
      selectedStack: stackSelection,
      customFiles,
      requestedFiles: mergeRequestedFiles(chatRequestedFiles, body.requestedFiles || []),
      filesToRemove,
      chatPendingCorrections: body.chatPendingCorrections || chatPendingCorrections,
      stackSelectionSource: stackSelection.source || "",
      isUserConfirmedStack: Boolean(stackSelection.isUserConfirmedStack || stackSelection.isDirty),
    }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Could not generate a preview.");
  }
  return payload;
}

function renderAgentAnalysis(analysis) {
  agentUnderstandingText.textContent = analysis.understanding || "No understanding available.";
  renderList(agentAssumptionsList, analysis.assumptions, "No assumptions recorded.");
  renderStackSummary(agentSuggestedStackList, analysis.suggestedStack || getDefaultStackState());
  resetQuestionFlow();
  renderQuestionFlow();
}

function renderQuestionFlow() {
  questionCards.replaceChildren();

  const questions = getQuestionList();
  if (questions.length === 0) {
    const empty = document.createElement("p");
    empty.className = "text-block";
    empty.textContent = "No follow-up questions are needed. Continue to finalize the recommended stack or skip straight to generation.";
    questionCards.appendChild(empty);
    refreshUiState();
    return;
  }

  const question = getCurrentQuestion();
  if (!question) {
    const completed = document.createElement("p");
    completed.className = "text-block";
    completed.textContent = "All important questions are complete. Continue to finalize your requirements.";
    questionCards.appendChild(completed);
    refreshUiState();
    return;
  }

  if (!currentQuestionDraft && getStoredAnswer(question.id) && !showingSuggestion) {
    setQuestionDraft(getStoredAnswer(question.id));
  }

  const card = document.createElement("article");
  card.className = "question-card active-question-card";

  const position = document.createElement("p");
  position.className = "question-position";
  position.textContent = `Question ${currentQuestionIndex + 1} of ${questions.length}`;

  const title = document.createElement("h4");
  title.textContent = question.question || "Question";

  const reason = document.createElement("p");
  reason.className = "question-reason";
  reason.textContent = "Type your preference, or use Let Agent Suggest to see the recommended answer and reason.";

  const inputLabel = document.createElement("label");
  inputLabel.className = "field-label";
  inputLabel.setAttribute("for", "activeQuestionInput");
  inputLabel.textContent = "Your answer";

  const input = document.createElement("input");
  input.type = "text";
  input.id = "activeQuestionInput";
  input.className = "question-input";
  input.placeholder = buildQuestionPlaceholder(question);
  input.value = currentQuestionDraft;
  input.addEventListener("input", (event) => {
    setQuestionDraft(event.target.value);
  });

  const quickActions = document.createElement("div");
  quickActions.className = "question-actions inline-question-actions";

  const suggestAnswerButton = document.createElement("button");
  suggestAnswerButton.type = "button";
  suggestAnswerButton.className = "ghost-button";
  suggestAnswerButton.textContent = "Let Agent Suggest";
  suggestAnswerButton.addEventListener("click", () => {
    showingSuggestion = true;
    renderQuestionFlow();
  });

  quickActions.appendChild(suggestAnswerButton);
  card.append(position, title, reason, inputLabel, input, quickActions);

  if (Array.isArray(question.options) && question.options.length) {
    const optionsHint = document.createElement("p");
    optionsHint.className = "question-hint";
    optionsHint.textContent = `Common choices: ${question.options.join(", ")}`;
    card.appendChild(optionsHint);
  }

  if (showingSuggestion) {
    const suggestionBlock = document.createElement("div");
    suggestionBlock.className = "suggestion-block";

    const suggestionTitle = document.createElement("p");
    suggestionTitle.className = "suggestion-title";
    suggestionTitle.textContent = `Suggested: ${question.default || "No default available"}`;

    const suggestionReason = document.createElement("p");
    suggestionReason.className = "suggestion-reason";
    suggestionReason.textContent = question.reason || "This default keeps the starter simple and runnable.";

    const suggestionActions = document.createElement("div");
    suggestionActions.className = "question-actions";

    const acceptButton = document.createElement("button");
    acceptButton.type = "button";
    acceptButton.className = "secondary-button";
    acceptButton.textContent = "Accept Suggestion";
    acceptButton.addEventListener("click", () => {
      storeQuestionAnswer(question.id, question.default || "");
      moveToNextQuestion();
    });

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.className = "ghost-button";
    editButton.textContent = "Edit Answer";
    editButton.addEventListener("click", () => {
      showingSuggestion = false;
      renderQuestionFlow();
      const inputElement = document.getElementById("activeQuestionInput");
      inputElement?.focus();
    });

    suggestionActions.append(acceptButton, editButton);
    suggestionBlock.append(suggestionTitle, suggestionReason, suggestionActions);
    card.appendChild(suggestionBlock);
  }

  questionCards.appendChild(card);
  refreshUiState();
}

function buildQuestionPlaceholder(question) {
  if (Array.isArray(question.options) && question.options.length) {
    return `Example: ${question.options[0]}`;
  }
  return "Type your answer or leave blank for a suggestion";
}

function storeQuestionAnswer(questionId, value) {
  agentAnswers[questionId] = String(value || "").trim();
}

function moveToNextQuestion() {
  showingSuggestion = false;
  currentQuestionIndex += 1;
  currentQuestionDraft = "";

  if (currentQuestionIndex >= getQuestionList().length) {
    renderQuestionFlow();
    void finalizeConversationOnly();
    return;
  }

  renderQuestionFlow();
  clearStatus();
}

async function finalizeConversationOnly() {
  setBusy(true, "Finalizing requirements...");

  try {
    await finalizeAgentConversation({ fillDefaults: false });
    setStatus("Requirements finalized. Generate the project when you are ready.", "success");
  } catch (error) {
    setStatus(error.message || "Could not finalize the requirements.", "error");
  } finally {
    clearBusyState();
  }
}

function buildAnswersPayload(fillDefaults) {
  const answers = { ...agentAnswers };
  if (!fillDefaults) {
    return answers;
  }

  getQuestionList().forEach((question) => {
    if (!answers[question.id]) {
      answers[question.id] = question.default || "";
    }
  });
  return answers;
}

function buildFinalizationSummary(finalizedStack, assumptions) {
  const scope = [
    finalizedStack.frontend && finalizedStack.frontend !== "None" ? finalizedStack.frontend : null,
    finalizedStack.backend && finalizedStack.backend !== "None" ? finalizedStack.backend : null,
  ].filter(Boolean).join(" + ");
  const firstAssumption = Array.isArray(assumptions) && assumptions.length ? assumptions[0] : "";
  return scope
    ? `The starter is now aligned around ${scope}. ${firstAssumption}`.trim()
    : `The starter requirements are finalized. ${firstAssumption}`.trim();
}

function renderFinalization(finalized) {
  finalizeCard.hidden = false;
  finalRequirementsText.textContent = finalized.finalRequirements || "No finalized requirements available.";
  finalizeSummaryText.textContent = buildFinalizationSummary(
    finalized.selectedStack || selectedStack,
    finalized.assumptions || [],
  );
  renderStackSummary(finalSelectedStackList, finalized.selectedStack || selectedStack);
  renderStackSummary(agentSuggestedStackList, finalized.selectedStack || selectedStack);
  const mergedAssumptions = dedupeList([
    ...(Array.isArray(agentAnalysis?.assumptions) ? agentAnalysis.assumptions : []),
    ...(Array.isArray(finalized.assumptions) ? finalized.assumptions : []),
  ]);
  renderList(agentAssumptionsList, mergedAssumptions, "No assumptions recorded.");
  refreshUiState();
}

function clearBusyState() {
  suggestButton.disabled = false;
  skipSuggestButton.disabled = false;
  askQuestionsButton.disabled = false;
  generationModeSelect.disabled = false;
  Object.values(stackSelects).forEach((select) => {
    select.disabled = false;
  });
  refreshUiState();
}

async function finalizeAgentConversation({ fillDefaults }) {
  const stackSelection = getCurrentStackSelection();
  const payload = await requestAgentFinalize({
    idea: baseIdea,
    answers: buildAnswersPayload(fillDefaults),
    suggestedStack: getStackFields(stackSelection),
  });
  finalRequirements = payload.finalRequirements || "";
  const finalizedStack = currentStackSelection.isDirty ? stackSelection : payload.selectedStack || stackSelection;
  applySelectedStackToControls(finalizedStack, {
    source: currentStackSelection.isDirty ? currentStackSelection.source : "confirmed_question_stack",
    isUserConfirmedStack: currentStackSelection.isDirty,
    isDirty: currentStackSelection.isDirty,
    lastModifiedField: currentStackSelection.lastModifiedField,
    lastModifiedAt: currentStackSelection.lastModifiedAt,
  });
  renderFinalization(payload);
  return payload;
}

async function generatePreviewFromCurrentState(successMessage) {
  const stackSelection = getCurrentStackSelection();
  setAgentActivity({
    understood: "done",
    analyzed: "done",
    migrated: "done",
    stack: "done",
    planned: "done",
    generated: "current",
    tools: "pending",
    validated: "pending",
    repaired: "pending",
    ready: "pending",
  });
  const payload = await requestPreview({
    idea: baseIdea,
    selectedStack: stackSelection,
    finalRequirements,
    customFiles: chatRequestedFiles,
    requestedFiles: chatRequestedFiles,
    filesToRemove: chatFilesToRemove,
    chatPendingCorrections,
  });
  currentPreview = payload;
  renderPreview(payload);
  applySelectedStackToControls(payload.selectedStack || stackSelection, {
    source: payload.stackSelectionSource || stackSelection.source,
    isUserConfirmedStack: stackSelection.isUserConfirmedStack,
    isDirty: stackSelection.isDirty,
    lastModifiedField: stackSelection.lastModifiedField,
    lastModifiedAt: stackSelection.lastModifiedAt,
  });
  setAgentActivity({
    generated: "done",
    tools: "done",
    validated: "done",
    repaired: "done",
    ready: "done",
  });
  setStatus(successMessage, "success");
  if (pendingAgentUpdate && !isApplyingPendingAgentUpdate) {
    const update = pendingAgentUpdate;
    pendingAgentUpdate = null;
    isApplyingPendingAgentUpdate = true;
    mergeChatActionState(update);
    try {
      return await generatePreviewFromCurrentState("Preview regenerated with pending chatbot correction.");
    } finally {
      isApplyingPendingAgentUpdate = false;
    }
  }
  return payload;
}

function resetAll() {
  baseIdea = "";
  agentAnalysis = null;
  agentAnswers = {};
  finalRequirements = "";
  currentPreview = null;
  selectedStack = getDefaultStackState();
  suggestedStack = getDefaultStackState();
  currentStackSelection = createCurrentStackSelection(getDefaultStackState(), {
    source: "initial_default",
  });
  chatMessages = [];
  chatDraftIdea = "";
  chatFinalRequirements = "";
  chatPendingCorrections = [];
  chatRequestedFiles = [];
  chatFilesToRemove = [];
  chatUpdatedStack = null;
  chatMode = "idea_discussion";
  chatLinkedPreviewId = "";
  pendingAgentUpdate = null;
  isApplyingPendingAgentUpdate = false;
  lastChatAction = null;
  llmModeUsed = "free_rule_based";
  chatModeBadge.textContent = "Free Rule Mode";
  chatActionBar.hidden = true;
  chatPanel.classList.remove("open", "is-open");
  chatPanel.classList.add("closed");
  chatToggleButton.classList.remove("open");
  chatToggleButton.classList.add("closed");
  renderChatMessages();
  resetQuestionFlow();
  resetAgentActivity();

  ideaInput.value = "";
  clearStatus();
  applySelectedStackToControls(getDefaultStackState());
  agentSection.hidden = true;
  advancedStackSection.hidden = true;
  previewSection.hidden = true;
  downloadSection.hidden = true;
  finalizeCard.hidden = true;
  generateProjectButton.disabled = true;
  generationModeSelect.value = "fast";
  generationModeSelect.disabled = false;
  downloadLink.removeAttribute("href");
  downloadLink.removeAttribute("download");
  downloadText.textContent = "Your generated project ZIP is ready.";

  agentUnderstandingText.textContent = "";
  clearCollection(agentAssumptionsList);
  clearCollection(agentSuggestedStackList);
  questionCards.replaceChildren();
  finalizeSummaryText.textContent = "";
  clearCollection(finalSelectedStackList);
  finalRequirementsText.textContent = "";

  clearCollection(detectedChoicesList);
  stackChips.replaceChildren();
  clearCollection(selectedStackList);
  clearCollection(toolRecommendationList);
  clearCollection(stackAnalysisList);
  clearCollection(migrationSummaryList);
  clearCollection(chosenStackList);
  clearCollection(assumptionsList);
  clearCollection(architectureList);
  clearCollection(packageRequirementsList);
  clearCollection(installCommandsList);
  clearCollection(runCommandsList);
  clearCollection(envVariablesList);
  requiredInputsBody.replaceChildren();
  modulesList.replaceChildren();
  filesList.replaceChildren();
  fileTreeBlock.textContent = "";
  summaryText.textContent = "";
  problemStatementText.textContent = "";
  mainFileText.textContent = "";
  runMethodText.textContent = "";
  localUrlText.textContent = "";
  runtimeInputsSummaryText.textContent = "";
  projectNameHeading.textContent = "Generated Project";
  refreshUiState();
}

function renderPreview(preview) {
  previewSection.hidden = false;
  setAgentActivity({
    understood: "done",
    stack: "done",
    planned: "done",
    generated: "done",
    validated: "done",
    repaired: "done",
    ready: "done",
  });
  projectNameHeading.textContent = preview.projectName || "Generated Project";
  summaryText.textContent = preview.summary || "No summary available.";
  problemStatementText.textContent = preview.problemStatement || "No problem statement available.";
  fileTreeBlock.textContent = preview.fileTree || "No file tree available.";
  renderRuntimeSummary(preview);

  renderList(detectedChoicesList, preview.detectedUserChoices, "No explicit user choices detected.");
  renderStackChips(preview.selectedStack || getDefaultStackState());
  renderStackSummary(selectedStackList, preview.selectedStack || getDefaultStackState());
  renderToolRecommendations(preview);
  renderStackAnalysis(preview.stackAnalysis || {});
  renderMigrationSummary(preview.migrationSummary || {});
  renderList(chosenStackList, preview.chosenStack, "No chosen stack details available.");
  renderList(assumptionsList, preview.assumptions, "No assumptions recorded.");
  renderList(architectureList, preview.architecture, "No architecture details available.");
  renderList(packageRequirementsList, preview.packageRequirements, "No package requirements available.");
  renderList(installCommandsList, preview.installCommands, "No install commands available.");
  renderList(runCommandsList, preview.runCommands, "No run commands available.");
  renderRequiredInputs(preview.requiredInputs || []);
  renderEnvVariables(preview.envVariables || []);
  renderModules(preview.modules || []);
  renderFiles(preview.files || [], preview.mainFile || "");
}

function renderRuntimeSummary(preview) {
  const requiredInputs = Array.isArray(preview.requiredInputs) ? preview.requiredInputs : [];
  mainFileText.textContent = preview.mainFile || "No main file detected.";
  runMethodText.textContent = preview.mainRunTarget || preview.primaryRunCommand || "No run method detected.";
  localUrlText.textContent = preview.localUrl || "Not applicable.";
  runtimeInputsSummaryText.textContent = requiredInputs.length
    ? `${requiredInputs.length} runtime input${requiredInputs.length === 1 ? "" : "s"} required before or during startup.`
    : "No required runtime inputs are needed for this project.";
}

function renderToolRecommendations(preview) {
  const items = [];
  if (preview.recommendedIde) {
    items.push(`Recommended IDE: ${preview.recommendedIde}`);
  }
  if (preview.alternativeIde) {
    items.push(`Alternative IDE: ${preview.alternativeIde}`);
  }
  if (Array.isArray(preview.runtimeTools) && preview.runtimeTools.length) {
    items.push(`Runtime Tools: ${preview.runtimeTools.join(", ")}`);
  }
  if (preview.packageManager) {
    items.push(`Package Manager: ${preview.packageManager}`);
  }
  renderList(toolRecommendationList, items, "No IDE recommendation available.");
}

function renderStackAnalysis(stackAnalysis) {
  const items = [];
  if (stackAnalysis.detectedLanguage) {
    items.push(`Language: ${stackAnalysis.detectedLanguage}`);
  }
  if (stackAnalysis.detectedFramework) {
    items.push(`Framework: ${stackAnalysis.detectedFramework}`);
  }
  if (stackAnalysis.projectType) {
    items.push(`Project Type: ${stackAnalysis.projectType}`);
  }
  if (stackAnalysis.architecturePattern) {
    items.push(`Architecture Pattern: ${stackAnalysis.architecturePattern}`);
  }
  renderList(stackAnalysisList, items, "No existing source stack was detected.");
}

function renderMigrationSummary(migrationSummary) {
  const items = [];
  if (migrationSummary.sourceLanguage || migrationSummary.sourceFramework) {
    items.push(
      `Source Stack: ${migrationSummary.sourceLanguage || "Unknown"} / ${migrationSummary.sourceFramework || "Unknown"}`,
    );
  }
  if (migrationSummary.targetLanguage || migrationSummary.targetFramework) {
    items.push(
      `Target Stack: ${migrationSummary.targetLanguage || "Unknown"} / ${migrationSummary.targetFramework || "Unknown"}`,
    );
  }
  if (migrationSummary.targetProjectType) {
    items.push(`Target Project Type: ${migrationSummary.targetProjectType}`);
  }
  if (Array.isArray(migrationSummary.keyChanges) && migrationSummary.keyChanges.length) {
    migrationSummary.keyChanges.forEach((item) => {
      items.push(`Change: ${item}`);
    });
  }
  renderList(migrationSummaryList, items, "No migration was needed for this project.");
}

function renderStackChips(stack) {
  stackChips.replaceChildren();
  const featuredChips = [
    ["language", "Language"],
    ["frontend", "Frontend"],
    ["backend", "Backend"],
    ["database", "Database"],
  ];

  featuredChips.forEach(([key, label]) => {
    const chip = document.createElement("span");
    chip.className = "stack-chip";
    chip.innerHTML = `<strong>${escapeHtml(label)}</strong> ${escapeHtml(stack[key] || "Auto")}`;
    stackChips.appendChild(chip);
  });
}

function renderList(element, items, fallback) {
  clearCollection(element);
  const safeItems = Array.isArray(items) && items.length ? items : [fallback];

  safeItems.forEach((item) => {
    const listItem = document.createElement("li");
    listItem.textContent = item;
    element.appendChild(listItem);
  });
}

function renderStackSummary(element, stack) {
  clearCollection(element);
  const labels = {
    language: "Language",
    frontend: "Frontend",
    backend: "Backend",
    database: "Database",
    aiTools: "AI / Tools",
    deployment: "Deployment",
  };

  Object.entries(labels).forEach(([key, label]) => {
    const listItem = document.createElement("li");
    listItem.textContent = `${label}: ${stack[key] || "Auto"}`;
    element.appendChild(listItem);
  });
}

function renderEnvVariables(envVariables) {
  clearCollection(envVariablesList);
  if (!Array.isArray(envVariables) || envVariables.length === 0) {
    renderList(envVariablesList, [], "No environment variables required.");
    return;
  }

  envVariables.forEach((variable) => {
    const listItem = document.createElement("li");
    const description = variable.description ? ` - ${variable.description}` : "";
    const value = variable.value ? ` = ${variable.value}` : "";
    listItem.textContent = `${variable.name}${value}${description}`;
    envVariablesList.appendChild(listItem);
  });
}

function renderRequiredInputs(requiredInputs) {
  requiredInputsBody.replaceChildren();
  if (!Array.isArray(requiredInputs) || requiredInputs.length === 0) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td colspan="5">No required runtime inputs are needed for this project.</td>
    `;
    requiredInputsBody.appendChild(row);
    return;
  }

  requiredInputs.forEach((item) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><code>${escapeHtml(item.name || "")}</code></td>
      <td>${item.required === false ? "Optional" : "Required"}</td>
      <td><code>${escapeHtml(item.example || "") || "-"}</code></td>
      <td>${escapeHtml(item.whereToEnter || item.whereToAdd || ".env")}</td>
      <td>${escapeHtml(item.purpose || "No purpose provided.")}</td>
    `;
    requiredInputsBody.appendChild(row);
  });
}

function renderModules(modules) {
  modulesList.replaceChildren();
  if (!Array.isArray(modules) || modules.length === 0) {
    const empty = document.createElement("p");
    empty.className = "text-block";
    empty.textContent = "No modules available.";
    modulesList.appendChild(empty);
    return;
  }

  modules.forEach((module) => {
    const card = document.createElement("article");
    card.className = "module-card";

    const title = document.createElement("h4");
    title.textContent = module.name || "Unnamed module";

    const purpose = document.createElement("p");
    purpose.textContent = module.purpose || "No purpose provided.";

    const keyFiles = document.createElement("p");
    keyFiles.className = "key-files";
    const files = Array.isArray(module.keyFiles) && module.keyFiles.length
      ? module.keyFiles.join(", ")
      : "No key files provided.";
    keyFiles.textContent = `Key files: ${files}`;

    card.append(title, purpose, keyFiles);
    modulesList.appendChild(card);
  });
}

function renderFiles(files, mainFile = "") {
  filesList.replaceChildren();
  if (!Array.isArray(files) || files.length === 0) {
    const empty = document.createElement("p");
    empty.className = "text-block";
    empty.textContent = "No starter files were generated.";
    filesList.appendChild(empty);
    return;
  }

  files.forEach((file) => {
    const entry = document.createElement("details");
    entry.className = "file-entry";

    const summary = document.createElement("summary");
    const isEntryPoint = mainFile && file.path === mainFile;
    summary.innerHTML = `
      <span class="file-entry-header">
        <span class="file-entry-dots"><span></span><span></span><span></span></span>
        <span class="file-entry-path">${escapeHtml(file.path || "Unnamed file")}</span>
      </span>
      <span class="file-entry-tag">${isEntryPoint ? "ENTRY POINT" : "Source"}</span>
    `;

    const code = document.createElement("pre");
    code.className = "code-block";
    code.textContent = file.content || "";

    entry.append(summary, code);
    filesList.appendChild(entry);
  });
}

function clearCollection(element) {
  element.replaceChildren();
}

function dedupeList(items) {
  return [...new Set((items || []).filter(Boolean))];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

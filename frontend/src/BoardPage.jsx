import { useState, useEffect, useCallback } from "react";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import { boardsAPI, cardsAPI, columnsAPI, membersAPI } from "./api"; // <-- ДОБАВИЛИ membersAPI
import { useAuth } from "./AuthContext";
import CardModal from "./CardModal";
import BoardSelector from "./BoardSelector";
import BoardMembers from "./BoardMembers";
import ColumnManager, { ColumnHeader } from "./ColumnManager";
import "./App.css";

const PRIORITY_LABELS = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
};

function parseBoardData(columnsData) {
  const newColumns = {};
  const newCards = {};
  const newOrder = [];

  columnsData.forEach((col) => {
    const columnId = String(col.column_id);
    newColumns[columnId] = {
      id: columnId,
      title: col.column_title,
      cardIds: col.cards.map((c) => String(c.id)),
    };
    col.cards.forEach((c) => {
      newCards[String(c.id)] = {
        ...c,
        id: String(c.id),
        assignee_id: c.assignee_id || null,
      };
    });
    newOrder.push(columnId);
  });

  return { newColumns, newCards, newOrder };
}

export default function BoardPage() {
  const { user, logout } = useAuth();
  const [board, setBoard] = useState(null);
  const [columns, setColumns] = useState({});
  const [cards, setCards] = useState({});
  const [columnOrder, setColumnOrder] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [addingToColumn, setAddingToColumn] = useState(null);
  const [newCardTitle, setNewCardTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [selectedCardId, setSelectedCardId] = useState(null);
  const [showMembers, setShowMembers] = useState(false);
  
  // <-- ДОБАВИЛИ СОСТОЯНИЕ ДЛЯ РОЛИ (1=owner, 2=writer, 3=reader)
  const [userRole, setUserRole] = useState(3);

  const loadBoardData = useCallback(async (boardId) => {
    const columnsData = await cardsAPI.getByBoard(boardId);
    const { newColumns, newCards, newOrder } = parseBoardData(columnsData);
    setColumns(newColumns);
    setCards(newCards);
    setColumnOrder(newOrder);
  }, []);

  const loadData = useCallback(async (boardId = null) => {
    try {
      setLoading(true);
      setError("");

      const boards = await boardsAPI.getMe();
      if (boards.length === 0) {
        setBoard(null);
        setColumns({});
        setCards({});
        setColumnOrder([]);
        setError("У вас нет досок. Создайте первую доску через «Мои доски».");
        return;
      }

      const selectedBoard = boardId
        ? boards.find((b) => b.id === boardId) || boards[0]
        : board?.id
          ? boards.find((b) => b.id === board.id) || boards[0]
          : boards[0];

      setBoard(selectedBoard);
      
      // <-- ПОЛУЧАЕМ РОЛЬ ПОЛЬЗОВАТЕЛЯ
      try {
        const membersData = await membersAPI.getByBoard(selectedBoard.id);
        const currentMember = membersData.members?.find(m => m.username === user?.username);
        setUserRole(currentMember?.role_id || 3); // 3 = reader по умолчанию
      } catch (err) {
        console.error("Не удалось получить роль:", err);
        setUserRole(3);
      }
      
      await loadBoardData(selectedBoard.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [board?.id, loadBoardData, user?.username]);

  useEffect(() => {
    loadData();
  }, []);

  const onDragEnd = async (result) => {
    const { destination, source, draggableId } = result;
    if (!destination) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index) return;

    const card = cards[draggableId];
    if (!card) return;

    const startColumn = columns[source.droppableId];
    const finishColumn = columns[destination.droppableId];
    const prevColumns = { ...columns };

    if (startColumn.id === finishColumn.id) {
      const newCardIds = Array.from(startColumn.cardIds);
      newCardIds.splice(source.index, 1);
      newCardIds.splice(destination.index, 0, draggableId);
      setColumns({ ...columns, [startColumn.id]: { ...startColumn, cardIds: newCardIds } });
    } else {
      const startCardIds = Array.from(startColumn.cardIds);
      startCardIds.splice(source.index, 1);
      const finishCardIds = Array.from(finishColumn.cardIds);
      finishCardIds.splice(destination.index, 0, draggableId);
      setColumns({
        ...columns,
        [startColumn.id]: { ...startColumn, cardIds: startCardIds },
        [finishColumn.id]: { ...finishColumn, cardIds: finishCardIds },
      });
    }

    try {
      const response = await cardsAPI.move(
        draggableId,
        destination.droppableId,
        destination.index,
        card.version
      );
      setCards((prev) => ({
        ...prev,
        [draggableId]: {
          ...prev[draggableId],
          version: response.new_version,
          column_id: destination.droppableId,
          position: destination.index,
        },
      }));
    } catch {
      setColumns(prevColumns);
      setError("Не удалось сохранить перемещение.");
      loadBoardData(board.id);
    }
  };

  const handleCreateCard = async (columnId) => {
    const title = newCardTitle.trim();
    if (!title) return;

    try {
      setCreating(true);
      setError("");
      const response = await cardsAPI.create(columnId, title);
      const cardId = String(response.card_id);

      setColumns((prev) => ({
        ...prev,
        [columnId]: {
          ...prev[columnId],
          cardIds: [...prev[columnId].cardIds, cardId],
        },
      }));
      setCards((prev) => ({
        ...prev,
        [cardId]: {
          id: cardId,
          title,
          description: "",
          priority: "medium",
          version: response.version ?? 1,
          column_id: columnId,
          assignee_id: null,
          assignee: null,
        },
      }));
      setNewCardTitle("");
      setAddingToColumn(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleCardSave = (updated) => {
    const assigneeUser = updated.assignee;
    setCards((prev) => ({
      ...prev,
      [updated.id]: {
        ...prev[updated.id],
        ...updated,
        id: String(updated.id),
        assignee: assigneeUser,
      },
    }));
  };

  const handleCardDelete = (cardId) => {
    const colId = cards[cardId]?.column_id;
    setCards((prev) => {
      const next = { ...prev };
      delete next[cardId];
      return next;
    });
    if (colId && columns[colId]) {
      setColumns((prev) => ({
        ...prev,
        [colId]: {
          ...prev[colId],
          cardIds: prev[colId].cardIds.filter((id) => id !== cardId),
        },
      }));
    }
    setSelectedCardId(null);
  };

  const handleColumnCreated = (column) => {
    setColumns((prev) => ({ ...prev, [column.id]: column }));
    setColumnOrder((prev) => [...prev, column.id]);
  };

  const handleColumnDelete = async (columnId) => {
    const prevColumns = { ...columns };
    const prevOrder = [...columnOrder];
    const deletedCardIds = columns[columnId]?.cardIds || [];

    setColumnOrder((prev) => prev.filter((id) => id !== columnId));
    setColumns((prev) => {
      const next = { ...prev };
      delete next[columnId];
      return next;
    });
    setCards((prev) => {
      const next = { ...prev };
      deletedCardIds.forEach((id) => delete next[id]);
      return next;
    });

    try {
      await columnsAPI.delete(columnId);
    } catch (err) {
      setColumns(prevColumns);
      setColumnOrder(prevOrder);
      setError(err.message);
      loadBoardData(board.id);
    }
  };

  const handleColumnRename = async (columnId, title) => {
    const prevTitle = columns[columnId]?.title;
    setColumns((prev) => ({
      ...prev,
      [columnId]: { ...prev[columnId], title },
    }));
    try {
      await columnsAPI.update(columnId, { title });
    } catch (err) {
      setColumns((prev) => ({
        ...prev,
        [columnId]: { ...prev[columnId], title: prevTitle },
      }));
      throw err;
    }
  };

  const handleSelectBoard = async (selectedBoard) => {
    setBoard(selectedBoard);
    setSelectedCardId(null);
    try {
      setLoading(true);
      await loadBoardData(selectedBoard.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBoardUpdated = (updatedBoard) => {
    setBoard(updatedBoard);
  };

  const handleBoardDeleted = async (deletedId) => {
    if (board?.id === deletedId) {
      setBoard(null);
      setSelectedCardId(null);
      await loadData();
    }
  };

  if (loading && !board) {
    return (
      <div className="app-container">
        <header className="header">
          <h1>Kanban</h1>
          <button onClick={logout} className="logout-btn">Выйти</button>
        </header>
        <div className="loading">Загрузка данных...</div>
      </div>
    );
  }

  if (error && columnOrder.length === 0 && !board) {
    return (
      <div className="app-container">
        <header className="header">
          <div className="header-left">
            <h1>Kanban</h1>
            {/* Читатель не может создавать доски, поэтому скрываем для него */}
            {userRole !== 3 && (
              <BoardSelector
                currentBoard={board}
                onSelectBoard={handleSelectBoard}
                onBoardUpdated={handleBoardUpdated}
                onBoardDeleted={handleBoardDeleted}
              />
            )}
          </div>
          <button onClick={logout} className="logout-btn">Выйти</button>
        </header>
        <div className="error-message">
          <p>{error}</p>
          <button onClick={() => loadData()} className="retry-btn">Попробовать снова</button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-left">
          <h1>{board?.title || "Kanban"}</h1>
          
          {/* Читатель не может редактировать/создавать доски */}
          {userRole !== 3 && (
            <BoardSelector
              currentBoard={board}
              onSelectBoard={handleSelectBoard}
              onBoardUpdated={handleBoardUpdated}
              onBoardDeleted={handleBoardDeleted}
            />
          )}
          
          {board && (
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => setShowMembers(true)}
            >
              Участники
            </button>
          )}
        </div>
        <div className="header-right">
          {user?.username && <span className="user-info">{user.username} ({userRole === 1 ? 'Владелец' : userRole === 2 ? 'Редактор' : 'Читатель'})</span>}
          <button onClick={logout} className="logout-btn">Выйти</button>
        </div>
      </header>

      {board?.description && (
        <p className="board-description">{board.description}</p>
      )}

      {error && <div className="board-error-banner">{error}</div>}

      <DragDropContext onDragEnd={onDragEnd}>
        <div className="board">
          {columnOrder.map((columnId) => {
            const column = columns[columnId];
            const cardIds = column?.cardIds || [];

            return (
              <Droppable key={columnId} droppableId={columnId}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={`column ${snapshot.isDraggingOver ? "column-drag-over" : ""}`}
                  >
                    <ColumnHeader
                      column={column}
                      onDelete={userRole !== 3 ? handleColumnDelete : undefined}
                      onRename={userRole !== 3 ? handleColumnRename : undefined}
                    />
                    <div className="card-list">
                      {cardIds.map((cardId, index) => {
                        const card = cards[cardId];
                        return (
                          <Draggable key={cardId} draggableId={cardId} index={index}>
                            {(provided, snapshot) => (
                              <div
                                ref={provided.innerRef}
                                {...provided.draggableProps}
                                {...provided.dragHandleProps}
                                className={`card ${snapshot.isDragging ? "card-dragging" : ""}`}
                                style={provided.draggableProps.style}
                                onClick={() => {
                                  // <-- ЧИТАТЕЛЬ НЕ МОЖЕТ ОТКРЫВАТЬ КАРТОЧКУ ДЛЯ РЕДАКТИРОВАНИЯ
                                  if (userRole !== 3 && !snapshot.isDragging) setSelectedCardId(cardId);
                                }}
                              >
                                <div className="card-title">{card?.title}</div>
                                {card?.description && (
                                  <div className="card-description">{card.description}</div>
                                )}
                                <div className="card-meta">
                                  {card?.priority && (
                                    <span className={`priority-badge priority-${card.priority}`}>
                                      {PRIORITY_LABELS[card.priority] || card.priority}
                                    </span>
                                  )}
                                  {card?.assignee && (
                                    <span className="assignee">{card.assignee}</span>
                                  )}
                                  {card?.deadline && (
                                    <span className="deadline">
                                      {new Date(card.deadline).toLocaleDateString("ru-RU")}
                                    </span>
                                  )}
                                </div>
                              </div>
                            )}
                          </Draggable>
                        );
                      })}
                      {provided.placeholder}
                    </div>

                    {/* <-- ЧИТАТЕЛЬ НЕ ВИДИТ КНОПКУ ДОБАВЛЕНИЯ КАРТОЧКИ */}
                    {userRole !== 3 && (
                      addingToColumn === columnId ? (
                        <div className="add-card-form">
                          <input
                            type="text"
                            placeholder="Название карточки"
                            value={newCardTitle}
                            onChange={(e) => setNewCardTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleCreateCard(columnId);
                              if (e.key === "Escape") {
                                setAddingToColumn(null);
                                setNewCardTitle("");
                              }
                            }}
                            autoFocus
                          />
                          <div className="add-card-actions">
                            <button
                              className="btn-primary btn-sm"
                              onClick={() => handleCreateCard(columnId)}
                              disabled={creating || !newCardTitle.trim()}
                            >
                              {creating ? "..." : "Добавить"}
                            </button>
                            <button
                              className="btn-secondary btn-sm"
                              onClick={() => {
                                setAddingToColumn(null);
                                setNewCardTitle("");
                              }}
                            >
                              Отмена
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          className="add-card-btn"
                          onClick={() => {
                            setAddingToColumn(columnId);
                            setNewCardTitle("");
                          }}
                        >
                          + Добавить карточку
                        </button>
                      )
                    )}
                  </div>
                )}
              </Droppable>
            );
          })}

          {/* <-- ЧИТАТЕЛЬ НЕ ВИДИТ КНОПКУ ДОБАВЛЕНИЯ КОЛОНКИ */}
          {userRole !== 3 && board && (
            <ColumnManager
              boardId={board.id}
              onColumnCreated={handleColumnCreated}
            />
          )}
        </div>
      </DragDropContext>

      {selectedCardId && cards[selectedCardId] && (
        <CardModal
          card={cards[selectedCardId]}
          onClose={() => setSelectedCardId(null)}
          onSave={handleCardSave}
          onDelete={handleCardDelete}
        />
      )}

      {showMembers && board && (
        <BoardMembers
          board={board}
          currentUserId={user?.username}
          onClose={() => setShowMembers(false)}
        />
      )}
    </div>
  );
}
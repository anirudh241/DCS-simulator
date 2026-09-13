"""Operator alarm summary display for the boiler-drum simulator."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from models.alarm import AlarmPriority, AlarmState


def format_simulation_time(seconds):
    """Format a simulation timestamp as HH:MM:SS.s."""
    total_tenths = max(0, round(float(seconds) * 10))
    total_seconds, tenths = divmod(total_tenths, 10)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{tenths}"


class AlarmTableModel(QAbstractTableModel):
    """Read-only presentation model backed by alarm-domain records."""

    COLUMNS = ("TIME", "PRIORITY", "TAG", "MESSAGE", "VALUE", "STATUS")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._records = ()

    def set_records(self, records):
        records = tuple(records)
        existing_ids = tuple(record.event_id for record in self._records)
        incoming_ids = tuple(record.event_id for record in records)

        if incoming_ids != existing_ids:
            self.beginResetModel()
            self._records = records
            self.endResetModel()
            return

        self._records = records
        if self._records:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._records) - 1, len(self.COLUMNS) - 1),
            )

    def record_at(self, row):
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
            and 0 <= section < len(self.COLUMNS)
        ):
            return self.COLUMNS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        record = self._records[index.row()]
        definition = record.definition

        if role == Qt.ItemDataRole.DisplayRole:
            values = (
                format_simulation_time(record.activated_at),
                definition.priority.name,
                definition.tag,
                definition.message,
                f"{record.value:.1f} {definition.unit}",
                record.state.value,
            )
            return values[index.column()]

        if role == Qt.ItemDataRole.ForegroundRole:
            if record.state is AlarmState.CLEARED:
                return QColor("#7f8993")
            if definition.priority is AlarmPriority.CRITICAL:
                return QColor("#ff9d9d")
            return QColor("#ffd28a")

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() in (0, 1, 2, 4, 5):
                return int(Qt.AlignmentFlag.AlignCenter)

        return None


class AlarmDashboard(QWidget):
    """Alarm history table plus acknowledgement controls."""

    acknowledge_requested = Signal(int)
    acknowledge_all_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alarmDashboard")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(10)
        root.addLayout(self._build_header())

        self.table_model = AlarmTableModel(self)
        self.table = QTableView()
        self.table.setObjectName("alarmTable")
        self.table.setModel(self.table_model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.selectionModel().selectionChanged.connect(
            self._update_selected_button
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        hint = QLabel(
            "Acknowledging confirms that the operator has seen an alarm; "
            "the alarm clears only after the process returns inside its limit."
        )
        hint.setObjectName("alarmHint")
        hint.setWordWrap(True)
        root.addWidget(hint)

    def _build_header(self):
        row = QHBoxLayout()
        title = QLabel("PROCESS ALARM SUMMARY")
        title.setObjectName("sectionTitle")
        row.addWidget(title)

        self.summary = QLabel("SYSTEM NORMAL")
        self.summary.setObjectName("alarmSummaryNormal")
        row.addWidget(self.summary)
        row.addStretch()

        self.acknowledge_selected = QPushButton("ACKNOWLEDGE SELECTED")
        self.acknowledge_selected.setObjectName("alarmAction")
        self.acknowledge_selected.clicked.connect(self._acknowledge_selection)
        row.addWidget(self.acknowledge_selected)

        self.acknowledge_all = QPushButton("ACKNOWLEDGE ALL")
        self.acknowledge_all.setObjectName("alarmAction")
        self.acknowledge_all.clicked.connect(
            lambda: self.acknowledge_all_requested.emit()
        )
        row.addWidget(self.acknowledge_all)
        return row

    def refresh(self, records, active_count, unacknowledged_count):
        selected_id = self.selected_event_id()
        self.table_model.set_records(records)
        self._restore_selection(selected_id)

        if active_count:
            self.summary.setText(
                f"{active_count} ACTIVE  |  {unacknowledged_count} UNACKNOWLEDGED"
            )
            summary_name = "alarmSummaryActive"
        else:
            self.summary.setText("SYSTEM NORMAL")
            summary_name = "alarmSummaryNormal"

        if self.summary.objectName() != summary_name:
            self.summary.setObjectName(summary_name)
            self.summary.style().unpolish(self.summary)
            self.summary.style().polish(self.summary)

        self.acknowledge_all.setEnabled(unacknowledged_count > 0)
        self._update_selected_button()

    def selected_event_id(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        record = self.table_model.record_at(rows[0].row())
        return record.event_id if record is not None else None

    def _restore_selection(self, event_id):
        if event_id is None:
            return
        for row in range(self.table_model.rowCount()):
            record = self.table_model.record_at(row)
            if record.event_id == event_id:
                self.table.selectRow(row)
                return

    def _acknowledge_selection(self):
        event_id = self.selected_event_id()
        if event_id is not None:
            self.acknowledge_requested.emit(event_id)

    def _update_selected_button(self, *_args):
        event_id = self.selected_event_id()
        enabled = False
        if event_id is not None:
            for row in range(self.table_model.rowCount()):
                record = self.table_model.record_at(row)
                if record.event_id == event_id:
                    enabled = record.active and not record.acknowledged
                    break
        self.acknowledge_selected.setEnabled(enabled)


ALARM_STYLESHEET = """
#alarmDashboard { background: #1b1f24; }
#alarmSummaryNormal, #alarmSummaryActive { padding: 5px 9px; font-family: Consolas; font-size: 10px; font-weight: 800; }
#alarmSummaryNormal { color: #9bd4a7; background: #24332a; border: 1px solid #3e6046; }
#alarmSummaryActive { color: #ffd28a; background: #3b3020; border: 1px solid #765b2e; }
#alarmTable { color: #d9dde1; background: #1e2227; alternate-background-color: #22272d; border: 1px solid #363e46; gridline-color: #343b43; selection-background-color: #354b53; selection-color: #f3f5f6; }
#alarmTable QHeaderView::section { color: #aeb6be; background: #272d33; border: 0; border-right: 1px solid #3d454d; border-bottom: 1px solid #3d454d; padding: 7px; font-size: 9px; font-weight: 800; }
#alarmAction { color: #d9dde1; background: #252a30; border: 1px solid #46505a; padding: 6px 10px; font-size: 9px; font-weight: 700; }
#alarmAction:hover { border-color: #d5a34d; }
#alarmAction:disabled { color: #636b73; background: #24282d; border-color: #343a40; }
#alarmHint { color: #818a94; font-size: 10px; }
"""

# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""RBAC Factories for ggrc models."""

from integration.ggrc.access_control.rbac_factories import (audit, assessment,
                                                            document, review,
                                                            assessment_template,  # noqa: E501
                                                            snapshot, issue,
                                                            program, workflow,
                                                            task_group,
                                                            task_group_task,
                                                            cycle,
                                                            cycle_task_group,
                                                            cycle_task,
                                                            cycle_task_entry,
                                                            evidence,
                                                            universal_factory)


TEST_FACTORIES_MAPPING = {
    "Audit": audit.AuditRBACFactory,
    "Assessment": assessment.AssessmentRBACFactory,
    "AssessmentTemplate": assessment_template.AssessmentTemplateRBACFactory,
    "Snapshot": snapshot.SnapshotRBACFactory,
    "Issue": issue.IssueRBACFactory,
    "Evidence": evidence.EvidenceRBACFactory,
    "Document": document.DocumentReferenceUrlRBACFactory,
    "Program": program.ProgramRBACFactory,
    "MappedReview": review.MappedReviewRBACFactory,
    "Workflow": workflow.WorkflowRBACFactory,
    "TaskGroup": task_group.TaskGroupRBACFactory,
    "TaskGroupTask": task_group_task.TaskGroupTaskRBACFactory,
    "Cycle": cycle.CycleRBACFactory,
    "CycleTaskGroup": cycle_task_group.CycleTaskGroupRBACFactory,
    "CycleTask": cycle_task.CycleTaskRBACFactory,
    "CycleTaskEntry": cycle_task_entry.CycleTaskEntryRBACFactory,
    "Universal": universal_factory.UniversalRBACFactory
}

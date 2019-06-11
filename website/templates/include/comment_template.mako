<script type="text/html" id="commentTemplate">
    <div class="comment-container" data-bind="attr:{id: id}">

        <div class="comment-body m-b-sm p-sm osf-box">
             <div data-bind="visible: loading">
                <i class="fa fa-spinner fa-spin"></i>
             </div>

            <div data-bind="ifnot: loading">
                <div data-bind="if: isDeletedAbuse">
                    <div>
                        <span class="text-muted">
                            <em>Comment confirmed as spam.</em>
                        </span>
                        <span data-bind="if: hasChildren()" class="comment-actions pull-right">
                            <i data-bind="css: toggleIcon, click: toggle"></i>
                        </span>
                    </div>
                </div>
                <div data-bind="if: isDeletedNotAbuse">
                    <div>
                        <span class="text-muted">
                            <em>Comment deleted.</em>
                        </span>
                        <span data-bind="if: hasChildren()" class="comment-actions pull-right">
                            <i data-bind="css: toggleIcon, click: toggle"></i>
                        </span>
                    </div>
                    <div data-bind="if: canEdit">
                        <a data-bind="click: submitUndelete">Restore</a>
                    </div>
                </div>

                <div data-bind="if: isAbuseNotDeleted">
                    <div>
                        <span class="text-muted">
                            <em>Comment reported.</em>
                        </span>
                        <span data-bind="if: hasChildren()" class="comment-actions pull-right">
                            <i data-bind="css: toggleIcon, click: toggle"></i>
                        </span>
                    </div>
                    <div data-bind="if: hasReport">
                        <a data-bind="click: submitUnreportAbuse">Not abuse</a>
                    </div>
                </div>

                <div data-bind="if: isVisible">

                    <div class="comment-info">
                        <form class="form-inline">
                            <span data-bind="if: author.profileImageUrl">
                                <img data-bind="css: {'comment-profile-image': author.profileImageUrl}, attr: {src: author.profileImageUrl}"/>
                            </span>
                            <span data-bind="if: author.id">
                                <a class="comment-author" data-bind="text: author.fullname, attr: {href: author.urls.profile}"></a>
                            </span>
                            <span data-bind="ifnot: author.id">
                                <span class="comment-author" data-bind="text: author.fullname"></span>
                            </span>
                            <span class="comment-date pull-right">
                                <span data-bind="template: {if: modified, afterRender: setupToolTips}">
                                    <a data-toggle="tooltip" data-bind="attr: {title: prettyDateModified()}">*</a>
                                </span>
                                <span data-bind="text: prettyDateCreated"></span>
                                &nbsp;
                            </span>
                        </form>
                    </div>

                    <div class="comment-content">

                        <div data-bind="ifnot: editing">
                            <span class="component-overflow" data-bind="html: contentDisplay"></span>
                            <span class="pull-right comment-actions" data-bind="if: hasChildren()">
                                <i data-bind="css: toggleIcon, click: toggle"></i>
                            </span>
                        </div>

                        <!--
                            Hack: Use template binding with if rather than vanilla if
                            binding to get access to afterRender
                        -->
                        <div data-bind="template: {if: editing, afterRender: autosizeText.bind($data)}">
                            <div class="form-group" style="padding-top: 10px">
                                <div class="form-control atwho-input comment-box" placeholder="Edit comment" data-bind="editableHTML: {observable: content, onUpdate: handleEditableUpdate}, attr: {maxlength: $root.MAXLENGTH}" contenteditable="true"></div>
                                <span data-bind="visible: editNotEmpty, text: counter, css: counterColor" class="pull-right label counter-comment"></span>
                            </div>
                            <div class="clearfix">
                                <div class="form-inline pull-right">
                                    <a class="btn btn-default btn-sm" data-bind="click: cancelEdit">Cancel</a>
                                    <span data-bind="tooltip: {title: errorMessage(), placement: 'bottom', disabled: !validateEdit()}">
                                        <a class="btn btn-success btn-sm" data-bind="click: submitEdit, css: {disabled: !validateEdit()}">Save</a>
                                    </span>
                                    <span data-bind="text: editErrorMessage" class="text-danger"></span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div>

                        <span>&nbsp;</span>

                        <!-- Action bar -->
                        <div style="display: inline">
                            <div data-bind="ifnot: editing" class="comment-actions pull-right">
                                <span data-bind="ifnot: isHam">
                                    <span data-bind="if: canEdit, click: edit">
                                        <i class="fa fa-pencil"></i>
                                    </span>
                                    <span data-bind="if: $root.canComment, click: showReply">
                                        <i class="fa fa-reply"></i>
                                    </span>
                                    <span data-bind="if: canReport, click: reportAbuse">
                                        <i class="fa fa-warning"></i>
                                    </span>
                                    <span data-bind="if: canEdit, click: startDelete">
                                        <i class="fa fa-trash-o"></i>
                                    </span>
                                </span>
                                <span data-bind="if: isHam">
                                    <span data-bind="if: $root.canComment, click: showReply">
                                        <i class="fa fa-reply"></i>
                                    </span>
                                    <span>
                                        <i class="text-success fa fa-check-circle-o"></i>
                                    </span>
                                </span>
                            </div>
                        </div>

                    </div>

                    <div class="comment-report clearfix" data-bind="if: reporting">
                        <form class="form-inline" data-bind="submit: submitAbuse">
                            <select class="form-control" data-bind="options: abuseOptions, optionsText: abuseLabel, value: abuseCategory"></select>
                            <input class="form-control" data-bind="value: abuseText" placeholder="Describe abuse" />
                        </form>
                        <div class="pull-right m-t-xs">
                            <a class="btn btn-default btn-sm" data-bind="click: cancelAbuse"> Cancel</a>
                            <a class="btn btn-danger btn-sm" data-bind="click: submitAbuse"> Report</a>
                        </div>
                    </div>

                    <div class="comment-delete clearfix m-t-xs" data-bind="if: deleting">
                        <div class="pull-right">
                            <a class="btn btn-default btn-sm" data-bind="click: cancelDelete">Cancel</a>
                            <a class="btn btn-danger btn-sm" data-bind="click: submitDelete">Delete</a>
                        </div>
                    </div>

                </div>
            </div>


        </div>

        <ul class="comment-list">

            <!-- ko if: replying -->

                <div data-bind="template: {afterRender: autosizeText.bind($data)}">
                    <div class="form-group" style="padding-top: 10px">
                        <div class="form-control atwho-input comment-box" placeholder="Add a comment" data-bind="editableHTML: {observable: replyContent, onUpdate: handleEditableUpdate}, attr: {maxlength: $root.MAXLENGTH}" contenteditable="true"></div>
                        <span data-bind="visible: replyNotEmpty, text: counter, css: counterColor" class="pull-right label counter-comment"></span>
                    </div>
                    <div class="clearfix">
                        <div class="pull-right">
                            <a class="btn btn-default btn-sm" data-bind="click: cancelReply, css: {disabled: submittingReply}"> Cancel</a>
                            <span data-bind="tooltip: {title: errorMessage(), placement: 'bottom', disabled: !validateReply()}">
                                <a class="btn btn-success btn-sm" data-bind="click: submitReply, css: {disabled: !validateReply() || submittingReply()}, text: commentButtonText"></a>
                            </span>
                            <span data-bind="text: replyErrorMessage" class="text-danger"></span>
                        </div>
                    </div>
                </div>

            <!-- /ko -->

            <!-- ko if: showChildren() -->
                <!-- ko template: {name:  'commentTemplate', foreach: comments} -->
                <!-- /ko -->
                <!-- ko if: urlForNext() -->
                <div class="row">
                    <button class="btn btn-link pull-right more-replies" type="button" data-bind="click: getMoreComments">More replies</button>
                </div>
                <!-- /ko -->
            <!-- /ko -->

        </ul>

    </div>

</script>

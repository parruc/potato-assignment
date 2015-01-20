# -*- coding: utf-8 -*-
import json

from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import UpdateView
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import requires_csrf_token
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse

from .models import Post
from .models import Tag
from .models import Comment
from .forms import PostForm
from .forms import CommentForm

import logging
logging.basicConfig()
logger = logging.getLogger("blog.console")


class HomepageView(ListView):
    """ Homepage view that get the 3 latest created posts
    """
    context_object_name = "posts"
    template_name = "blog/homepage.html"
    queryset = Post.objects.all()[:3]


class PostsView(ListView):
    """ View that shows all the posts sorted by creation and paginated
    """
    model = Post
    context_object_name = "posts"
    template_name = "blog/posts.html"
    paginate_by = 2


class PostView(DetailView):
    """ The detail view of a single post
    """
    context_object_name = "post"
    template_name = "blog/post.html"
    model = Post

    def get_context_data(self, **kwargs):
        queryset = super(PostView, self).get_context_data(**kwargs)
        comments = Comment.objects.filter(post=queryset['post'])
        queryset.update({"comments": comments,
                         "form": CommentForm()})
        return queryset


class PostEdit(UpdateView):
    """ Edit a single post
    """
    template_name = "blog/post_edit.html"
    model = Post
    form_class = PostForm

    @method_decorator(requires_csrf_token)
    @method_decorator(login_required)
    @method_decorator(permission_required("blog.post_edit"))
    def dispatch(self, *args, **kwargs):
        return super(PostEdit, self).dispatch(*args, **kwargs)


class PostAdd(CreateView):
    """ Add a single post
    """
    template_name = "blog/post_add.html"
    form_class = PostForm

    @method_decorator(requires_csrf_token)
    @method_decorator(login_required)
    @method_decorator(permission_required('blog.post_add'))
    def dispatch(self, *args, **kwargs):
        return super(PostAdd, self).dispatch(*args, **kwargs)


class TagsView(ListView):
    """ View that shows all the tags
    """
    model = Tag
    context_object_name = "tags"
    template_name = "blog/tags.html"
    paginate_by = 2


class TagView(DetailView):
    """ The detail view of a single tag
    """
    model = Tag
    context_object_name = "tag"
    template_name = "blog/tag.html"


class JSONResponseMixin(object):
    def render_to_response(self, context, **httpresponse_kwargs):
        "Returns a JSON response containing 'context' as payload"
        return self.get_json_response(self.convert_context_to_json(context),
                                      **httpresponse_kwargs)

    def get_json_response(self, content, **httpresponse_kwargs):
        "Construct an `HttpResponse` object."
        return HttpResponse(content,
                            content_type='application/json',
                            **httpresponse_kwargs)

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        return json.dumps(context)


class JSONFormMixin(JSONResponseMixin):
    def form_invalid(self, form):
        context = self.get_context_data(form=form,
                                        success=False)
        return self.render_to_response(context)

    def form_valid(self, form):
        self.object = form.save()
        context = self.get_context_data(form=form,
                                        obj=self.object,
                                        success=True)
        return self.render_to_response(context)


class JSONDeletionMixin(JSONFormMixin):

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        context = self.get_context_data(success=True)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        success = kwargs.get('success', False)
        json.dumps({"success": success})


class JSONPostDelete(JSONDeletionMixin, DeleteView):
    """ Remove a single post
    """

    model = Post

    @method_decorator(requires_csrf_token)
    @method_decorator(login_required)
    @method_decorator(permission_required('blog.post_delete'))
    def dispatch(self, *args, **kwargs):
        return super(JSONPostDelete, self).dispatch(*args, **kwargs)


class JSONCommentAdd(JSONFormMixin, CreateView):
    """ View to add comment. Posting to this from post.html
    """
    model = Comment

    @method_decorator(requires_csrf_token)
    def dispatch(self, *args, **kwargs):
        return super(JSONCommentAdd, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        success = kwargs.get('success', False)
        options = kwargs.get('options', {})
        to_json = {}
        fields = {}
        to_json.update(options=options)
        to_json.update(success=success)

        if not success:
            form = kwargs.get('form')
            for field_name, field in form.fields.items():
                fields[field_name] = unicode(form[field_name].value())
            to_json.update(fields=fields)
            if form.errors:
                errors = {'non_field_errors': form.non_field_errors()}
            fields = {}
            for field_name, text in form.errors.items():
                fields[field_name] = text
            errors.update(fields=fields)
            to_json.update(errors=errors)
        else:
            obj = kwargs.get('obj')
            to_json.update({"title": obj.title,
                            "text": obj.text,
                            "author": obj.author,
                            "created": obj.created.strftime("%Y-%m-%d")})
        return json.dumps(to_json)


class JSONTagsView(JSONResponseMixin, ListView):

    model = Tag

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        return [(tag.pk, tag.title) for tag in queryset]

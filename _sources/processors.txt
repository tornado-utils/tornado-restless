.. module:: processors

:mod:`processors` -- Request preprocessors and postprocessors
=============================================================

Preprocessor are functions that get called before a instance is returned / modified / deleted / created.
Similiar postprocessors are called after the event directly before the output is returned.

The preprocessor / postprocessor keyword argument of the create_api_blueprint method is a dictionary
of method name to function.

The keyword argument model is a wrapper around the the sqlalchemy instance for the blueprint.
Handler is the blueprint class itself.

:mod:`processors.preprocessors` -- Request preprocessors
--------------------------------------------------------

Modifing the following keywords inplace changes the behaviour of the called method:

Arguments:
 :instance_id: This is a list of ids for which instance gets modified.
               For example a call to GET /api/person/1 would call get_single with instance_id = ['1']
     :filters:      The extracted list of filters from the request as alchemy filters.
                         Add or remove of filters will modify the instances that gets affected.
                         You can use :func:tornado_restless.wrapper._is_ordering_expression if you want to
                         distinguish between a real filter and a order_by clause
     :data:         Dictionary of the fields that get applied.

    Additonal Arguments:
      :model: Wrapper around the sqlalchemy model for this blueprint
              Supports a bunch of helping functions
      :handler: The BaseHandler blueprint instance

    Methods:
     ANY ::

      def prepare(model: ModelWrapper, handler: BaseHandler):
          """ Called for any request """

 :http:method:`get` ::

      def get(search_params: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called for a GET request """

      def get_single(instance_id: list, model: ModelWrapper, handler: BaseHandler):
          """ Called on a single GET request """
          pass

      def get_many(filters: list, model: ModelWrapper, handler: BaseHandler):
          """ Called on a many GET request """
          pass

 :http:method:`post` ::

      def post(search_params: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called for a POST request """
          pass

      def post_single(data: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called on a single POST request """
          pass

 :http:method:`delete` ::

      def delete(search_params: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called for a DELETE request """
          pass

      def delete_single(instance_id: list, model: ModelWrapper, handler: BaseHandler):
          """ Called on a single DELETE request """
          pass

      def delete_many(filters: list, model: ModelWrapper, handler: BaseHandler):
          """ Called on a many DELETE request """
          pass

 :http:method:`patch` / :http:method:`put` ::

      def patch(search_params: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called for a PATCH request """

      def patch_single(instance_id: list, data: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called on a single PATCH request """
          pass

      def patch_many(filters: list, data: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called on a many PATCH request """
          pass

To hold the processing raise any exception in the function. If you want to set the returned a status code and
a somehow meaningfull error message use tornado.web.HTTPError or a subclass. For example for a general authentification
layer you could use somewhat similiar to::

      def check_auth(model: ModelWrapper, handler: BaseHandler, **kw):

          # Get the current user
          current_user = handler.current_user

          # Check for authorisation
          if not is_authorized_to_modify(current_user, model):
               raise HTTPError(status_code=401, log_message='Not Authorized')

      manager.create_api(Person, preprocessor=dict(prepare=[check_auth]))

Queries without an instance_id are translated to a search according the filters/orders parameters of "q".
If you want for example always to return your elements in ascending order you can add an GET_MANY preprocessor::

      def order_asc(filters: list, model: ModelWrapper, handler: BaseHandler, **kw):

          # Apply the asc filter
          filters.append(model.asc())

      manager.create_api(Person, preprocessor=dict(get_many=[order_asc]))


:mod:`processors.postprocessors` -- Request postprocessors
----------------------------------------------------------

Modifing the following keywords inplace changes the behaviour of the output

Arguments:
 :result: The dictionary representation of the output bevour JSON encoding but after flatten.

    Additonal Arguments:
      :model: Wrapper around the sqlalchemy model for this blueprint
              Supports a bunch of helping functions
      :handler: The BaseHandler blueprint instance

    Methods:
     ANY ::

      def on_finish(model: ModelWrapper, handler: BaseHandler):
          """ Called after any request """

 :http:method:`get` ::

      def get(result: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called after a GET request """

 :http:method:`post` ::

      def post(result: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called after a POST request """

 :http:method:`delete` ::

      def delete(result: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called after a DELETE request """

 :http:method:`patch` / :http:method:`put` ::

      def patch(result: dict, model: ModelWrapper, handler: BaseHandler):
          """ Called after a PATCH request """


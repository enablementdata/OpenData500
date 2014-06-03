from base import *
import json

#--------------------------------------------------------LOGIN PAGE------------------------------------------------------------
class LoginHandler(BaseHandler): 
    @tornado.web.addslash
    def get(self):
        self.render(
            "login.html", 
            next=self.get_argument("next","/"), 
            message=self.get_argument("error",""),
            page_title="Please Login",
            page_heading="Login to OD500" 
            )

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "").encode('utf-8')
        try: 
            user = models.Users.objects.get(username=username)
        except Exception, e:
            logging.info('unsuccessful login')
            error_msg = u"?error=" + tornado.escape.url_escape("User does not exist")
            self.redirect(u"/login" + error_msg)
        if user and user.password and bcrypt.hashpw(password, user.password.encode('utf-8')) == user.password:
            logging.info('successful login for '+username)
            self.set_current_user(username)
            self.redirect("/")
        else: 
            logging.info('unsuccessful login')
            error_msg = u"?error=" + tornado.escape.url_escape("Incorrect Password")
            self.redirect(u"/login" + error_msg)

    def set_current_user(self, user):
        logging.info('setting ' + user)
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else: 
            self.clear_cookie("user")

#--------------------------------------------------------REGISTER PAGE------------------------------------------------------------
class RegisterHandler(LoginHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        if self.current_user == "luis":
            self.render(
                "register.html", 
                next=self.get_argument("next","/"),
                page_title="Register",
                page_heading="Register for OD500"
                )
        else:
            self.render('404.html',
                page_heading="I'm afraid I can't let you do that.",
                user=self.current_user,
                page_title="Forbidden",
                error="Not Enough Priviliges")

    @tornado.web.authenticated
    def post(self):
        username = self.get_argument("username", "")
        try:
            user = models.Users.objects.get(username=username)
        except:
            user = ''
        if user:
            error_msg = u"?error=" + tornado.escape.url_escape("Login name already taken")
            self.redirect(u"/register" + error_msg)
        else: 
            password = self.get_argument("password", "")
            hashedPassword = bcrypt.hashpw(password, bcrypt.gensalt(8))
            country = self.get_argument("country", None)
            newUser = models.Users(
                username=username,
                password = hashedPassword,
                country=country
                )
            newUser.save()
            self.set_current_user(username)
            self.redirect("/")


#--------------------------------------------------------LOGOUT HANDLER------------------------------------------------------------
class LogoutHandler(BaseHandler): 
    def get(self):
        self.clear_cookie("user")
        #self.clear_cookie("country")
        self.redirect(u"/login")


#--------------------------------------------------------ADMIN PAGE------------------------------------------------------------
class CompanyAdminHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
        country = user.country
        logging.info("Working in: " + country)
        #Check if there is a user logged in:
        if self.current_user:
            surveySubmitted = models.Company.objects(Q(submittedSurvey=True) & Q(vetted=True) & Q(country=country)).order_by('prettyName')
            sendSurveys = models.Company.objects(Q(submittedSurvey=False) & Q(country=country))
            needVetting = models.Company.objects(Q(submittedSurvey=True) & Q(vetted=False) & Q(country=country)).order_by('-lastUpdated', 'prettyName')
            stats = models.Stats.objects.get(country=country)
            self.render(
                "admin_companies.html",
                page_title='OpenData500',
                page_heading='Admin - ' + country.upper(),
                surveySubmitted = surveySubmitted,
                needVetting = needVetting,
                user=self.current_user,
                sendSurveys = sendSurveys,
                stats = stats
            )
        else: #if no user is logged in, go to not allowed page
            self.render('404.html',
                page_heading="I'm afraid I can't let you do that.",
                user=self.current_user,
                page_title="Forbidden",
                error="Not Enough Priviliges")

    def post(self):
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
        action = self.get_argument("action", None)
        country = user.country
        if action == "refresh":
            self.application.stats.refresh_stats(country)
            self.application.files.generate_visit_csv()
            stats = models.Stats.objects.get(country=country)
            self.write({"totalCompanies": stats.totalCompanies, "totalCompaniesWeb":stats.totalCompaniesWeb, "totalCompaniesSurvey":stats.totalCompaniesSurvey})
        elif action == "files":
            self.application.files.generate_company_json()
            # self.application.files.generate_agency_json()
            self.application.files.generate_company_csv()
            self.application.files.generate_company_all_csv()
            # self.application.files.generate_agency_csv()
            self.write("success")
        elif action == "vizz":
            #self.application.files.generate_sankey_json()
            self.application.files.generate_chord_chart_files()
            self.write("success")
        elif action == 'display':
            try:
                id = self.get_argument("id", None)
                c = models.Company.objects.get(id=bson.objectid.ObjectId(id))
            except Exception, e:
                logging.info("Error: " + str(e))
                self.write(str(e))
            c.display = not c.display
            c.save()
            self.application.stats.update_all_state_counts()
            self.write("success")
        elif action == 'agency_csv':
            self.application.files.generate_agency_csv()
            self.write("success")
        elif action == 'company_csv':
            self.application.files.generate_company_csv()
            self.write("success")
        elif action == 'company_all_csv':
            self.application.files.generate_company_all_csv()
            self.write("success")


#--------------------------------------------------------ADMIN AGENCIES PAGE------------------------------------------------------------
class AgencyAdminHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        logging.info("temp")




#--------------------------------------------------------COMPANY EDIT (ADMIN) PAGE------------------------------------------------------------
class AdminEditCompanyHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self, id):
        try: 
            company = models.Company.objects.get(id=bson.objectid.ObjectId(id))
            page_heading = "Editing " + company.companyName + ' (Admin)'
            page_title = "Editing " + company.companyName + ' (Admin)'
        except Exception, e:
            logging.info('Error: ' + str(e))
            self.render("404.html",
                page_heading = '404 - Company Not Found',
                page_title = '404 - Not Found',
                error = "404 - Not Found",
                user=self.current_user,
                message=id)
        self.render("adminEditCompany.html",
            page_title = page_title,
            page_heading = page_heading,
            company = company,
            companyType = companyType,
            companyFunction = companyFunction,
            criticalDataTypes = criticalDataTypes,
            revenueSource = revenueSource,
            categories=categories,
            datatypes = datatypes,
            stateList = stateList,
            stateListAbbrev=stateListAbbrev,
            user=self.current_user,
            id = str(company.id)
        )

    @tornado.web.authenticated
    def post(self, id):
        #print all arguments to log:
        logging.info("Admin Editing Company")
        logging.info(self.request.arguments)
        #get the company you will be editing
        company = models.Company.objects.get(id=bson.objectid.ObjectId(id))
        #------------------CONTACT INFO-------------------
        company.contact.firstName = self.get_argument("firstName", None)
        company.contact.lastName = self.get_argument("lastName", None)
        company.contact.title = self.get_argument("title", None)
        company.contact.org = self.get_argument("org", None)
        company.contact.email = self.get_argument("email", None)
        company.contact.phone = self.get_argument("phone", None)
        try: 
            if self.request.arguments['contacted']:
                company.contact.contacted = True
        except:
            company.contact.contacted = False
        #------------------CEO INFO-------------------
        company.ceo.firstName = self.get_argument("ceoFirstName", None)
        company.ceo.lastName = self.get_argument("ceoLastName", None)
        #------------------COMPANY INFO-------------------
        company.companyName = self.get_argument("companyName", None)
        company.prettyName = re.sub(r'([^\s\w])+', '', company.companyName).replace(" ", "-").title()
        company.url = self.get_argument('url', None)
        company.city = self.get_argument('city', None)
        company.state = self.get_argument('state', None)
        company.zipCode = self.get_argument('zipCode', None)
        company.companyType = self.get_argument("companyType", None)
        if company.companyType == 'other': #if user entered custom option for Type
            company.companyType = self.get_argument('otherCompanyType', None)
        company.yearFounded = self.get_argument("yearFounded", 0)
        if  not company.yearFounded:
            company.yearFounded = 0
        company.fte = self.get_argument("fte", 0)
        if not company.fte:
            company.fte = 0
        company.companyCategory = self.get_argument("category", None)
        if company.companyCategory == "Other":
            company.companyCategory = self.get_argument("otherCategory", None)
        try: #try and get all checked items. 
            company.revenueSource = self.request.arguments['revenueSource']
        except: #if no checked items, then make it into an empty array (form validation should prevent this always)
            company.revenueSource = []
        if 'Other' in company.revenueSource: #if user entered a custom option for Revenue Source
            del company.revenueSource[company.revenueSource.index('Other')] #delete 'Other' from list
            if self.get_argument('otherRevenueSource', None):
                company.revenueSource.append(self.get_argument('otherRevenueSource', None)) #add custom option to list.
        company.description = self.get_argument('description', None)
        company.descriptionShort = self.get_argument('descriptionShort', None)
        company.financialInfo = self.get_argument('financialInfo', None)
        company.datasetWishList = self.get_argument('datasetWishList', None)
        company.sourceCount = self.get_argument('sourceCount', None) 
        company.dataComments = self.get_argument('dataComments', None)
        company.filters = [company.companyCategory, company.state] #re-do filters
        for a in company.agencies:
                if a.prettyName:
                    company.filters.append(a.prettyName)
        if self.get_argument("submittedSurvey", None) == "submittedSurvey":
            company.submittedSurvey = True
            company.filters.append("survey-company")
        else:
            company.submittedSurvey = False
        if self.get_argument("vettedByCompany", None) == "vettedByCompany":
            company.vettedByCompany = False
        else:
            company.vettedByCompany = True
        if self.get_argument("vetted", None) == "vetted":
            company.vetted = True
        else: 
            company.vetted = False
        if self.get_argument("display", None) == "display":
            company.display = True
        else: 
            company.display = False
        if self.get_argument("locked", None) == "locked":
            company.locked = True
        else: 
            company.locked = False
        #company.lastUpdated = datetime.now()
        company.notes = self.get_argument("notes", None)
        company.save()
        self.application.stats.update_all_state_counts()
        self.write('success')
        #self.redirect('/thanks/')
        # if self.get_argument('submit', None) == 'Save and Submit':
        #     self.redirect('/')
        # if self.get_argument('submit', None) == 'Save And Continue Editing':
        #     self.redirect('/edit/'+id)




#--------------------------------------------------------DELETE COMPANY------------------------------------------------------------
class DeleteCompanyHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, id):
        try:
            company = models.Company.objects.get(id=bson.objectid.ObjectId(id)) 
        except:
            self.render(
                "404.html",
                page_title='404 - Open Data500',
                page_heading='Oh no...',
                error = "404 - Not Found"
            )
        # #-----REMOVE FROM ALL AGENCIES-----
        agencies = models.Agency.objects(usedBy__in=[str(company.id)])
        for a in agencies:
            #-----REMOVE DATASETS (AGENCY)-----
            temp = []
            temp_print = []
            for d in a.datasets:
                if d.usedBy != company:
                    temp.append(d)
                    temp_print.append(d.usedBy.companyName)
            a.datasets = temp
            logging.info(temp_print)
            #---REMOVE DATASETS (SUBAGENCY)---
            for s in a.subagencies:
                temp = []
                temp_print = []
                for d in s.datasets:
                    if company != d.usedBy:
                        temp.append(d)
                        temp_print.append(d.usedBy.companyName)
                s.datasets = temp
                logging.info(temp_print)
                #--REMOVE FROM SUBAGENCIES--
                if company in s.usedBy:
                    s.usedBy.remove(company)
            #-----REMOVE FROM AGENCY----
            a.usedBy.remove(company)
            a.usedBy_count = len(a.usedBy)
            a.save()
        ##----------DELETE COMPANY--------
        company.delete()
        self.redirect('/admin/')






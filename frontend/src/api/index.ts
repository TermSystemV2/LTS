import request from '../utils/request';

export const fetchData = () => {
    return request({
        url: './table.json',
        method: 'get'
    });
};

// 规范数据类型
interface LoginInfo {
	username: string;
	password: string;
	grant_type:string;
	scope:string;
	client_id:string;
	client_secret:string;
}

export const login = (data:LoginInfo) => {
    let grant_type = data.grant_type;
    let username = data.username;
    let password = data.password;
    let scope = data.scope;
    let client_id = data.client_id;
    let client_secret = data.client_secret;
    return request({
        url: 'proxy/apis/v1/login',
        method: 'post',
        data:'grant_type='+grant_type+'&username='+username+'&password='+password+'&scope='+scope+'&client_id='+client_id+'&client_secret='+client_secret
    });
};

export const fetchExcellentBarData = () => {
    return request({
        url:'proxy/apis/v1/excellentInfoHist',
        method: 'get'
    });
};

export const fetchExcellentLineData = () => {
    return request({
        url: 'proxy/apis/v1/excellentInfoLine',
        method: 'get'
    });
};

export const fetchCoursesData = (term:String) => {
    return request({
        url: 'proxy/apis/v1/scores/courses/<term>',
        method: 'post',
        data:{
            "term":term
        }
    });
};

export const fetchGradesData = (term:String) => {
    return request({
        url: 'proxy/apis/v1/scores/grade/<term>',
        method: 'post',
        data:{
            "term":term
        }
    });
};

export const fetchClassesData = (term:String) => {
    return request({
        url: 'proxy/apis/v1/scores/class/chart/<term>',
        method: 'post',
        data:{
            "term":term
        }
    });
};

export const fetchStudntInfoData = (term:String) => {
    return request({
        url: 'proxy/apis/v1/studentInfo/grade/?grade='+term,
        method: 'get'
    });
};

export const fetchStudentClasssesData = () => {
    return request({
        url: 'proxy/apis/v1/stuclasses',
        method: 'get'
    });
};

export const fetchAnalysisData = (term: String,classesName: String) => {
    return request({
        url: 'proxy/apis/v1/students/analysis',
        method: 'post',
        data:{
            "stuTermBar": term,
            "stuClassID": classesName
          }
    });
};

export const fetchUsersData = () => {
    return request({
        url: 'proxy/apis/v1/users',
        method: 'get'
    });
};

interface userInfo {
	cID: string;
	cName: string;
	is_active: boolean;
	is_superuser: boolean;
    password: string
}
export const addUserData = (data:userInfo) => {
    return request({
        url: 'proxy/apis/v1/users',
        method: 'post',
        data
    });
};